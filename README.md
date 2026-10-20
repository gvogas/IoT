# IoT

Fridge monitor: an ESP32 with 2 DHT11 sensors sends the temperature and humidity over MQTT,
and a Flask website shows the fridges and signs up customers.

There is one fan, with a separate driver in hardware/fan.py.
Admins can turn it off from the fridge dashboard.
Sensor readings do not switch it automatically. The planned email approval flow
for readings below a fridge's threshold is not implemented yet.

## Folders

```
app.py              run this: website (customer sign up + fridge dashboard)
config.py           all the settings: broker ip, GPIO pins, database path

models/             talks to the database (database.py, customer.py, fridge.py)
controllers/        MqttController receives readings; FanController controls the shared fan
hardware/           talks to the Pi pins (fan.py, signals.py = LEDs + buzzer)
routes/             Flask pages and API endpoints for auth, customers, fridges and fan
templates/          the HTML pages
static/             shared CSS and page JavaScript (signup.js, fridge_dashboard.js)
tools/              database setup and customer role management
mail/               standalone email scripts (not connected to sensor readings yet)
esp32/fridge/       ESP32 code (both DHT11 sensors on one board), open fridge.ino in Arduino IDE
docs/               project documents (Phase 2 PDF)
```

## Setup

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

Only run `python -m controllers.mqtt_controller` alone to test sensor reception without the website, never at the same time as app.py.

Models hold customer and fridge data. Controllers handle MQTT and the shared fan.
Routes receive browser requests and call the models or controllers. Templates and
static files display the pages. The fan and MQTT controller instances are shared
within the application process.

## Tools

```
python -m tools.set_role          make a customer an admin (or a normal customer again)
```

First admin: sign up on the website, then run `python -m tools.set_role` and give yourself the admin role.

To start over with an empty database: delete `store.db` and run `python -m tools.init_database` again.
