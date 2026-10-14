import paho.mqtt.client as mqtt

frig1 = "frig1/temperature"
frig1h = "frig1/humidity"
frig2 = "frig2/temperature"
frig2h = "frig2/humidity"

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")

    client.subscribe(frig1)
    client.subscribe(frig1h)
    client.subscribe(frig2)
    client.subscribe(frig2h)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+": "+str(msg.payload))

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

#school ip
mqttc.connect("192.168.50.107", 1883, 60)

#home
#mqttc.connect("192.168.50.107", 1883, 60)

mqttc.loop_forever()
