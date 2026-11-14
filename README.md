# IoT

A small self-checkout store with two monitored fridges, running on a Raspberry Pi.

Customers scan their items with an RFID reader, sign in with a membership card and pay at the checkout.
Each purchase earns loyalty points, and the receipt is emailed to them automatically.
They can see their purchases and points, and email a receipt again, from My Account.
Admins manage products, stock and customers on the website.
Their dashboard shows today's sales against yesterday and lists what needs attention, and the Reports page has the sales, profit and tax for any period.
They get an email when a sale leaves a product low or out of stock, and when a delivery restocks it.
The language picker in the top bar shows the pages in 11 languages, and the receipt email follows it.

For the fridges, an ESP32 with 2 DHT11 sensors sends the temperature and humidity over MQTT,
and the website shows them live.

There is one fan, with a separate driver in hardware/fan.py.
When a fridge goes over its threshold, the app emails an alert. Replying YES turns the fan on, and the fridge pages have a button to turn it on or off.
Admins can turn it off from the fridge dashboard. Sensor readings never switch it by themselves.

Fridge 3 has a Minew MSP01 sensor instead, which measures the temperature, humidity and light, and sees movement.
It talks Bluetooth, so the Pi hears it with reelyActive's [barnowl](https://github.com/reelyactive/barnowl) (msp01/index.js)
and passes the readings to MQTT. Fridge 3 works like the other fridges (limit, alert emails, history), and the
admin dashboard has cards for all of the MSP01's readings.

For a map of how all the parts fit together, see [docs/architecture.md](docs/architecture.md).

## Folders

```
app.py              run this: starts the website, the MQTT controller and the inbox check
config.py           all the settings: broker ip, GPIO pins, database path

routes/             Flask pages and API endpoints, one file per area. guards.py has the sign in checks
models/             talks to the database (database.py has query, query_one, execute and transaction)
controllers/        MqttController receives readings; FanController controls the shared fan
hardware/           talks to the fan, the RFID reader and the MSP01 listener (fan.py, rfid.py, msp01.py)
mail/               sends the alerts and receipts, and reads the YES/NO replies. translations.py has the receipt email in each language
tools/              database setup and customer role management
templates/          the HTML pages and the emails, one folder per area
static/uploads/     product images uploaded on the website (not in git, back it up along with store.db)
static/css/         theme.css has every colour, components.css has the layout
static/js/          common.js and language.js run on every page, table_filter.js is shared by the lists, then one folder per area
esp32/fridge/       ESP32 code (both DHT11 sensors on one board), open fridge.ino in Arduino IDE
msp01/              Node.js program that hears the MSP01 sensor over Bluetooth with barnowl and publishes to MQTT
docs/               project documents
logs/               app.log and its older copies, made by app.py (not in git)
```

## Theme

The colours are the Arctic Reflection palette: `#5289AD`, `#243C4C`, `#ACBCBF`, `#F4FCFB` and `#698696`. They are all at the top of [static/css/theme.css](static/css/theme.css), so changing a value there changes every page.

The pages load Bootstrap, its icons and the Inter font from a CDN, so the browser needs internet to show them properly. Any language other than English also needs internet, because Google Translate does the translating.

## Setup

The settings files have passwords, so they are not in git. Make your own copies first:

```
cp config.example.py config.py
cp esp32/fridge/config.example.h esp32/fridge/config.h
```

**Already set up and pulling new code?** Compare your `config.py` with `config.example.py` and copy over any settings you don't have yet (like the `MSP01_*` and `MQTT_USERNAME` / `MQTT_PASSWORD` lines). The app stops with an `ImportError` until they are there. Then run `python -m tools.init_database` to add any new tables, and `pip install -r requirements.txt`.

Then fill in your own values:

| File | Setting | What to put |
|---|---|---|
| config.py | `MQTT_BROKER` | IP of the Pi running the MQTT broker |
| config.py | `MQTT_USERNAME`, `MQTT_PASSWORD` | The broker's login. Leave both empty if the broker has no password (see [docs/fridges.md](docs/fridges.md#putting-a-password-on-the-broker)) |
| config.py | `ALERT_EMAIL` | Gmail account that sends the alerts and receipts |
| config.py | `ALERT_EMAIL_PASSWORD` | Gmail app password for that account (not the normal password) |
| config.py | `ALERT_TO` | Email address that gets the fridge alerts. Stock emails go to the admin accounts, and only use this if there are no admins |
| config.py | `FRIDGES_ENABLED` | `False` to run without the broker, ESP32 and sensors |
| config.py | `MSP01_ENABLED` | `True` to listen for the MSP01 sensor, add it as a fridge and show its cards on the dashboard |
| config.py | `MSP01_FRIDGE_ID` | The fridge the MSP01 is in (3). `python -m tools.init_database` adds that fridge |
| config.py | `MSP01_ADDRESS` | The MSP01's Bluetooth address, like `C3:00:00:45:5D:A6`. Empty uses the first one heard, and prints its address |
| config.py | `RFID_PORT` | USB serial port of the RFID reader, like `/dev/ttyUSB0` |
| config.h | `WIFI_SSID`, `WIFI_PASSWORD` | WiFi the ESP32 joins |
| config.h | `MQTT_BROKER` | Same IP as `MQTT_BROKER` in config.py |
| config.h | `MQTT_USER`, `MQTT_PASS` | The ESP32's broker login. Delete both lines if the broker has no password |

The email settings can also come from the `ALERT_EMAIL`, `ALERT_EMAIL_PASSWORD` and `ALERT_TO` environment variables.

The Pi doesn't recognise the CF600's USB id, so after a reboot `/dev/ttyUSB0` is missing. When `RFID_PORT` isn't there, app.py runs `sudo modprobe usbserial vendor=0x0483 product=0x5750` to create it, so it may ask for your password when it starts. If the reader still isn't found, it logs an error and the app keeps running. The full guide (protocol, API, troubleshooting) is in [docs/rfid-reader.md](docs/rfid-reader.md).

```
python -m venv .venv
.venv\Scripts\activate          (Windows)
source .venv/bin/activate       (Pi)

pip install -r requirements.txt
python -m tools.init_database
```

`requirements.txt` pins the exact version of every package, so every install matches the Pi. To upgrade one, run `pip install --upgrade <name>`, test the app, then change its version in the file.

For the MSP01 sensor, install the Node.js packages once. `npm run privileges` lets Node use the Pi's Bluetooth without sudo (it runs `sudo setcap cap_net_raw+eip` on node, as barnowl-hci asks):

```
sudo apt install nodejs npm     (if node isn't there yet)
cd msp01
npm install
npm run privileges
cd ..
```

Set up the MSP01 in the BeaconSET+ app (default password `minew123`) as in reelyActive's guide, https://reelyactive.github.io/diy/minew-msp01-config/. Keep the INFO slot, and turn on the HT (temperature and humidity), PIR and light sensor slots. The full guide (finding the address, MQTT topics, troubleshooting) is in [docs/msp01.md](docs/msp01.md).

## Run

Always run from the project folder.

```
python app.py               then go to http://127.0.0.1:5000/
                            (also sets up the RFID port and starts the MQTT controller for sensor readings)
                            The admin pages need a customer with the admin role (see below)
```

When someone opens a page, a route in routes/ handles it. The route asks the models for data from
the database, or asks a controller for the live readings and the fan, then fills in a template.
There is only one MQTT controller and one fan controller, and the whole app shares them.

Everything the app reports (sensor problems, emails sent, YES replies, errors) goes to the screen and to `logs/app.log`. Look there first when something stops working on the Pi.

## Tools

```
python -m tools.set_role          make a customer an admin (or a normal customer again)
```

To make the first admin, sign up on the website (it needs a membership card barcode, scanned or typed), then run `python -m tools.set_role` and give yourself the admin role. Stock emails go to the email on every admin account.

To start over with an empty database, delete `store.db` and run `python -m tools.init_database` again.

