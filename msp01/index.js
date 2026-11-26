// Hears the Minew MSP01 sensor in Fridge 3 over Bluetooth and publishes its readings to MQTT.
//
// It uses reelyActive's packages (github.com/reelyactive/barnowl):
//   barnowl + barnowl-hci  listen on the Pi's Bluetooth (hci0). Everything they hear comes out
//                          as a "raddec": who sent it, how strong, the packets, and when
//   advlib                 decodes the packets. advlib-ble-services knows the Minew packets
//   mqtt                   publishes each reading, like "msp01/temperature" -> "22.0"
//
// app.py starts this with `node msp01/index.js` when MSP01_ENABLED is True in config.py,
// and passes the settings below. MqttController (controllers/mqtt_controller.py) receives the readings.
//
// Setup, once:  cd msp01 && npm install && npm run privileges

const Barnowl = require("barnowl");
const BarnowlHci = require("barnowl-hci");
const advlib = require("advlib");
const mqtt = require("mqtt");

// Settings from config.py (app.py passes them). The values after || are used if you run it by hand
const MQTT_BROKER = process.env.MQTT_BROKER || "localhost";
const MQTT_PORT = process.env.MQTT_PORT || "1883";
const TOPIC = process.env.MSP01_TOPIC || "msp01";
// Like "c30000455da6". Empty = the first MSP01 we hear
let chosen = (process.env.MSP01_ADDRESS || "").replace(/:/g, "").toLowerCase();

// How advlib decodes a Bluetooth packet (from advlib's README)
const PROCESSORS = [
    {
        processor: require("advlib-ble"),
        libraries: [require("advlib-ble-services"), require("advlib-ble-manufacturers")],
        options: { ignoreProtocolOverhead: true },
    },
];

// After advlib decodes a Minew packet, its uri is a link about Minew, like
// "https://sniffypedia.org/Organization/Shenzhen_Minew_Technologies_Co_Ltd/"
function isMinew(data) {
    return typeof data.uri === "string" && data.uri.includes("Minew");
}

// The broker's username and password, if it has one (MQTT_USERNAME and MQTT_PASSWORD in config.py)
const client = mqtt.connect(`mqtt://${MQTT_BROKER}:${MQTT_PORT}`, {
    username: process.env.MQTT_USERNAME || undefined,
    password: process.env.MQTT_PASSWORD || undefined,
    // Don't keep readings in memory while the broker is down. Old readings are no use later
    queueQoSZero: false,
});
client.on("connect", () => console.log(`MSP01: connected to MQTT at ${MQTT_BROKER}`));
client.on("error", (err) => console.log(`MSP01: MQTT problem: ${err.message}`));

// Send one reading, like publish("temperature", 22.0)
function publish(name, value) {
    client.publish(`${TOPIC}/${name}`, String(value));
}

// What we heard, for the status lines below
let lastHeard = 0;          // when we last heard our sensor (ms), 0 = not yet
let connected = false;      // are we hearing it now?
let nearby = {};            // other MSP01s we heard, like { "c30000455da6": -70 }

// Seconds of silence before we say the sensor is lost
const LOST_AFTER = 30;

// enableMixing joins what the radio heard from one device within a second into one raddec
const barnowl = new Barnowl({ enableMixing: true });
try {
    barnowl.addListener(BarnowlHci, {}, BarnowlHci.SocketListener, {});
} catch (err) {
    console.log(`MSP01: can't use Bluetooth: ${err.message}`);
    console.log("MSP01: run this once, then start the app again:  cd msp01 && npm run privileges");
    process.exit(1);
}

barnowl.on("raddec", (raddec) => {
    if (!raddec.packets || raddec.packets.length === 0) return;

    // Like { batteryPercentage: 100, temperature: 22.04, relativeHumidity: 28.82, uri: "https://sniffypedia.org/..." }
    const data = advlib.process(raddec.packets, PROCESSORS);
    if (!isMinew(data)) return;
    const rssi = raddec.rssiSignature[0].rssi;

    if (!chosen) {
        chosen = raddec.transmitterId;
        console.log(`MSP01: using the sensor ${chosen}. Put it in MSP01_ADDRESS in config.py to always use this one`);
    }
    // Another MSP01, like a classmate's. Remember it for the "not found" line
    if (raddec.transmitterId !== chosen) {
        nearby[raddec.transmitterId] = rssi;
        return;
    }

    lastHeard = Date.now();
    if (!connected) {
        connected = true;
        console.log(`MSP01: connected, hearing ${chosen} (signal ${rssi} dBm)`);
    }

    // advlib's names -> our MQTT topics
    if (data.temperature !== undefined) publish("temperature", data.temperature.toFixed(1));
    if (data.relativeHumidity !== undefined) publish("humidity", data.relativeHumidity.toFixed(1));
    // Light level. Our MSP01s send luminousFlux, other Minew sensors illuminance
    if (data.luminousFlux !== undefined) publish("light", data.luminousFlux);
    if (data.illuminance !== undefined) publish("light", data.illuminance);
    // Only light or dark, on some versions. advlib gives a list like [true]
    if (data.isLightDetected !== undefined) publish("bright", data.isLightDetected[0] ? 1 : 0);
    if (data.isMotionDetected !== undefined) publish("motion", data.isMotionDetected[0] ? 1 : 0);
    if (data.batteryPercentage !== undefined) publish("battery", data.batteryPercentage);
    // Signal strength in dBm, closer to 0 is stronger. The Pi is the only receiver
    publish("rssi", rssi);
});

// Every 10 seconds: say if we lost the sensor, or which MSP01s we can hear if we can't find ours
setInterval(() => {
    const silent = (Date.now() - lastHeard) / 1000;
    if (connected && silent > LOST_AFTER) {
        connected = false;
        console.log(`MSP01: lost ${chosen}, nothing heard for ${Math.round(silent)} s`);
    }
    if (!connected) {
        const others = Object.keys(nearby).map((id) => `${id} (${nearby[id]} dBm)`);
        const looking = chosen ? `not hearing ${chosen}` : "no MSP01 heard yet";
        console.log(`MSP01: ${looking}. Other MSP01s nearby: ${others.length ? others.join(", ") : "none"}`);
    }
    nearby = {};
}, 10000);

console.log(`MSP01: listening on Bluetooth with barnowl, looking for ${chosen || "any MSP01"}`);
