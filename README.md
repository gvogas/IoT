# IoT

Fridge monitor: an ESP32 with 2 DHT11 sensors sends the temperature and humidity over MQTT,
and a Flask website shows the fridges and signs up customers.

There is one fan, with a separate driver in hardware/fan.py.
When a fridge goes over its threshold, the app emails an alert. Replying YES turns the fan on.
Admins can turn it off from the fridge dashboard. Sensor readings never switch it by themselves.

For a map of how all the parts fit together, see [docs/architecture.md](docs/architecture.md).

## Folders

```
app.py              run this: website 
config.py           all the settings: broker ip, GPIO pins, database path 

models/             talks to the database (database.py has query, query_one and execute; customer.py, fridge.py, reading.py)
controllers/        MqttController receives readings; FanController controls the shared fan
hardware/           talks to the Pi pins (fan.py, signals.py = LEDs + buzzer)
routes/             Flask pages and API endpoints for auth, customers, fridges and fan
templates/          the HTML pages
static/             shared CSS and page JavaScript (signup.js, fridge_dashboard.js)
tools/              database setup and customer role management
mail/               sends the temperature alert and reads the YES/NO replies
esp32/fridge/       ESP32 code (both DHT11 sensors on one board), open fridge.ino in Arduino IDE
docs/               project documents
```

## Setup

The settings files have passwords, so they are not in git. Make your own copies first:

```
cp config.example.py config.py
cp esp32/fridge/config.example.h esp32/fridge/config.h
```

Then fill in your own values:

| File | Setting | What to put |
|---|---|---|
| config.py | `MQTT_BROKER` | IP of the Pi running the MQTT broker |
| config.py | `ALERT_EMAIL` | Gmail account that sends the alerts |
| config.py | `ALERT_EMAIL_PASSWORD` | Gmail app password for that account (not the normal password) |
| config.py | `ALERT_TO` | Email address that gets the alerts |
| config.py | `FRIDGES_ENABLED` | `False` to run without the broker, ESP32 and sensors |
| config.h | `WIFI_SSID`, `WIFI_PASSWORD` | WiFi the ESP32 joins |
| config.h | `MQTT_BROKER` | Same IP as `MQTT_BROKER` in config.py |

The email settings can also come from the `ALERT_EMAIL`, `ALERT_EMAIL_PASSWORD` and `ALERT_TO` environment variables.

```
python -m venv .venv
.venv\Scripts\activate          (Windows)
source .venv/bin/activate       (Pi)

pip install -r requirements.txt
python -m tools.init_database
```

## Run

Always run from the project folder.

```
python app.py               then go to http://127.0.0.1:5000/
                            (also starts the MQTT controller for sensor readings)
                            Fridges + Customers need a customer with the admin role (see below)
```

When someone opens a page, a route in routes/ handles it. The route asks the models for data from
the database, or asks a controller for the live readings and the fan, then fills in a template.
There is only one MQTT controller and one fan controller, and the whole app shares them.

## Tools

```
python -m tools.set_role          make a customer an admin (or a normal customer again)
```

To make the first admin, sign up on the website, then run `python -m tools.set_role` and give yourself the admin role.

To start over with an empty database, delete `store.db` and run `python -m tools.init_database` again.

