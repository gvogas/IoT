# IoT

Fridge monitor: an ESP32 with 2 DHT11 sensors sends the temperature and humidity over MQTT,
the Raspberry Pi turns the fan on when a fridge is over its threshold,
and a Flask website shows the fridges and signs up customers.

## Folders

```
app.py              run this: website (customer sign up + fridge dashboard)
mqtt_server.py      run this: turns the fan on/off from the temperature
init_db.py          run once: makes store.db
config.py           all the settings: broker ip, GPIO pins, database path

models/             talks to the database (db.py, customer.py, fridge.py)
hardware/           talks to the Pi pins (fan.py, signals.py = LEDs + buzzer)
routes/             the Flask pages (customer_routes.py, fridge_routes.py)
templates/          the HTML pages
static/             files the pages load: css/, js/ (gauges), images/ (fan + thermometer icons)
tools/              scripts you run by hand to test things
mail/               send / read email scripts (temperature alert + YES reply)
esp32/fridge/       ESP32 code (both DHT11 sensors on one board), open fridge.ino in Arduino IDE
docs/               project documents (Phase 2 PDF, task description table)
```

## Setup

```
python -m venv .venv
.venv\Scripts\activate          (Windows)
source .venv/bin/activate       (Pi)

pip install -r requirements.txt
python init_db.py
```

## Run

Always run from the project folder.

```
python app.py               then go to http://127.0.0.1:5000/
                            (also starts mqtt_server.py: sensor readings + fan control)
                            Fridges + Customers need a customer with the admin role (see below)
```

Only run `python mqtt_server.py` alone to test the fan without the website, never at the same time as app.py.

## Tools

```
python -m tools.set_role          make a customer an admin (or a normal customer again)
```

First admin: sign up on the website, then run `python -m tools.set_role` and give yourself the admin role.

To start over with an empty database: delete `store.db` and run `python init_db.py` again.
