# IoT

A small self-checkout store with two monitored fridges, running on a Raspberry Pi.

Customers scan their items with an RFID reader, sign in with a membership card and pay at the checkout.
They can see their purchases and email their receipts from My Account.
Admins manage products, stock and customers on the website.

For the fridges, an ESP32 with 2 DHT11 sensors sends the temperature and humidity over MQTT,
and the website shows them live.

There is one fan, with a separate driver in hardware/fan.py.
When a fridge goes over its threshold, the app emails an alert. Replying YES turns the fan on.
Admins can turn it off from the fridge dashboard. Sensor readings never switch it by themselves.

For a map of how all the parts fit together, see [docs/architecture.md](docs/architecture.md).

## Folders

```
app.py              run this: starts the website, the MQTT controller and the inbox check
config.py           all the settings: broker ip, GPIO pins, database path

routes/             Flask pages and API endpoints, one file per area. guards.py has the sign in checks
models/             talks to the database (database.py has query, query_one, execute and transaction)
controllers/        MqttController receives readings; FanController controls the shared fan
hardware/           talks to the Pi pins and the RFID reader (fan.py, signals.py, rfid.py)
mail/               sends the alerts and receipts, and reads the YES/NO replies
tools/              database setup and customer role management
templates/          the HTML pages, one folder per area
static/uploads/     product images uploaded on the website (not in git, back it up along with store.db)
static/css/         theme.css has every colour, components.css has the layout
static/js/          common.js runs on every page, table_filter.js is shared by the lists, then one folder per area
esp32/fridge/       ESP32 code (both DHT11 sensors on one board), open fridge.ino in Arduino IDE
docs/               project documents
```

## Theme

The colours are the Arctic Reflection palette: `#5289AD`, `#243C4C`, `#ACBCBF`, `#F4FCFB` and `#698696`. They are all at the top of [static/css/theme.css](static/css/theme.css), so changing a value there changes every page.

The pages load Bootstrap, its icons and the Inter font from a CDN, so the browser needs internet to show them properly.

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
| config.py | `ALERT_EMAIL` | Gmail account that sends the alerts and receipts |
| config.py | `ALERT_EMAIL_PASSWORD` | Gmail app password for that account (not the normal password) |
| config.py | `ALERT_TO` | Email address that gets the alerts |
| config.py | `FRIDGES_ENABLED` | `False` to run without the broker, ESP32 and sensors |
| config.py | `RFID_PORT` | USB serial port of the RFID reader, like `/dev/ttyUSB0` |
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
                            The admin pages need a customer with the admin role (see below)
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

