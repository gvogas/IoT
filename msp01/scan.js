// Lists the MSP01 sensors that are on and in range, so you know what to put in MSP01_ADDRESS.
// Run it with:  cd msp01 && npm run scan
// It listens for 15 seconds with barnowl, then prints each sensor it heard.

const Barnowl = require("barnowl");
const BarnowlHci = require("barnowl-hci");
const advlib = require("advlib");

// How long to listen (seconds)
const LISTEN_FOR = 15;

// How advlib decodes a Bluetooth packet (same as index.js)
const PROCESSORS = [
    {
        processor: require("advlib-ble"),
        libraries: [require("advlib-ble-services"), require("advlib-ble-manufacturers")],
        options: { ignoreProtocolOverhead: true },
    },
];

// Each MSP01 we heard, like { "c30000455da6": { rssi: -61, battery: 100, temperature: 22.0, heard: 4 } }
const sensors = {};

const barnowl = new Barnowl({ enableMixing: true });
try {
    barnowl.addListener(BarnowlHci, {}, BarnowlHci.SocketListener, {});
} catch (err) {
    console.log(`Can't use Bluetooth: ${err.message}`);
    console.log("Run this once, then try again:  npm run privileges");
    process.exit(1);
}

barnowl.on("raddec", (raddec) => {
    if (!raddec.packets || raddec.packets.length === 0) return;
    const data = advlib.process(raddec.packets, PROCESSORS);
    // Only Minew sensors (their uri is a link about Minew)
    if (typeof data.uri !== "string" || !data.uri.includes("Minew")) return;

    const sensor = sensors[raddec.transmitterId] || { heard: 0 };
    sensor.heard += 1;
    sensor.rssi = raddec.rssiSignature[0].rssi;
    if (data.batteryPercentage !== undefined) sensor.battery = data.batteryPercentage;
    if (data.temperature !== undefined) sensor.temperature = data.temperature;
    sensors[raddec.transmitterId] = sensor;
});

console.log(`Listening for MSP01 sensors for ${LISTEN_FOR} seconds...`);

setTimeout(() => {
    const ids = Object.keys(sensors);
    if (ids.length === 0) {
        console.log("No MSP01 heard. Press the button on the sensor to wake it, then try again.");
        process.exit(0);
    }

    // Strongest signal first: that one is probably the closest
    ids.sort((a, b) => sensors[b].rssi - sensors[a].rssi);
    console.log(`\n${ids.length} MSP01 on:\n`);
    for (const id of ids) {
        const s = sensors[id];
        // "c30000455da6" -> "C3:00:00:45:5D:A6", the way config.py writes it
        const address = id.toUpperCase().match(/../g).join(":");
        const temperature = s.temperature === undefined ? "--" : s.temperature.toFixed(1);
        const battery = s.battery === undefined ? "--" : s.battery;
        console.log(`  ${address}   signal ${s.rssi} dBm   battery ${battery} %   ${temperature} °C   heard ${s.heard} times`);
    }
    console.log('\nPut the one you want in config.py, like  MSP01_ADDRESS = "' + ids[0].toUpperCase().match(/../g).join(":") + '"');
    process.exit(0);
}, LISTEN_FOR * 1000);
