import sqlite3
import paho.mqtt.client as mqtt

from fan import Fan

frig1 = "frig1/temperature"
frig1h = "frig1/humidity"
frig2 = "frig2/temperature"
frig2h = "frig2/humidity"

# Fan on the Pi through the motor driver (BCM pin numbers)
fan = Fan(22, 27, 17)

# temperature topic -> (fridgeID in customer.db, fan topic, fan); None = no fan wired yet
fans = {
    frig1: (1, "frig1/fan", fan),
    frig2: (2, "frig2/fan", None),
}

def get_threshold(fridge_id):
    conn = sqlite3.connect("customer.db")
    row = conn.execute("SELECT temp_threshold FROM Fridge WHERE fridgeID = ?", (fridge_id,)).fetchone()
    conn.close()
    return row[0] if row else None

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")

    client.subscribe(frig1)
    client.subscribe(frig1h)
    client.subscribe(frig2)
    client.subscribe(frig2h)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    value = msg.payload.decode().strip()
    print(msg.topic+": "+value)

    # Turn the fridge's fan on when its temperature is over the threshold
    if msg.topic in fans:
        fridge_id, fan_topic, fridge_fan = fans[msg.topic]
        threshold = get_threshold(fridge_id)
        if threshold is None:
            return
        state = "ON" if float(value) > threshold else "OFF"

        if fridge_fan:
            if state == "ON":
                fridge_fan.on()
            else:
                fridge_fan.off()

        # So the dashboard can show the fan state
        client.publish(fan_topic, state, retain=True)
        print(f"  threshold {threshold} -> {fan_topic} {state}")

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

#school ip
mqttc.connect("192.168.50.107", 1883, 60)

#home
#mqttc.connect("192.168.50.107", 1883, 60)

try:
    mqttc.loop_forever()
finally:
    fan.cleanup()
