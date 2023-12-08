from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import mysql.connector
import sqlite3
from random import uniform
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
import pytz
import geocoder
import openmeteo_requests
import requests_cache
from retry_requests import retry

app = Flask(__name__)

# MQTT configurations
MQTT_BROKER = ""
MQTT_PORT = 8883
MQTT_TOPIC = "esp32/pub"
MQTT_REQUEST_TOPIC = 'esp32/sub'
MQTT_CA_PATH = ""
MQTT_CERT_PATH = ""
MQTT_KEY_PATH = ""

last_day = 0

humidityColors, humidityColors_year, humidityColors_month, humidityColors_day = [],[],[],[]
# Email configuration
smtp_server = 'smtp.gmail.com'
smtp_port = 587
smtp_username = ''
smtp_password = ''
# Message details
from_email = ''
to_email = ''
subject = 'Humidity warning'

connection = sqlite3.connect('sensor_data.db')
cursor = connection.cursor()
create_table_query = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY,
    device_id VARCHAR(255),
    humidity FLOAT,
    temperature FLOAT,
    timestamp TEXT -- or use INTEGER for storing timestamps
);
"""
cursor.execute(create_table_query)
if cursor.rowcount > 0:
    print("Created new sensor_data table.")
else:
    print("Table already exists.")
connection.commit()
connection.close()

def on_connect(client, userdata, flags, rc, properties=None):
    print("Connection returned result: " + str(rc) )
    client.subscribe(MQTT_TOPIC , 1)

def on_message(client, userdata, msg):
    global last_day
    print('START Message')
    payload = json.loads(msg.payload.decode("utf-8"))
    device_id = payload.get("device_id")
    temperature = payload.get("temperature")
    humidity = payload.get("humidity")
    timestamp = payload.get("time")
    print('Send email in function')
    # send_email()
    datetime_object = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    if datetime_object.hour == 8 and datetime_object.weekday() != last_day:
        send_email()
        last_day = datetime_object.weekday()
    print('PAYLOAD:', payload)
    try:
        connection = sqlite3.connect('sensor_data.db')
        cursor = connection.cursor()
        sql = "INSERT INTO sensor_data (device_id, temperature, humidity, timestamp) VALUES (?, ?, ?, ?)"
        val = (device_id, temperature, humidity, datetime_object,)
        cursor.execute(sql, val)
        connection.commit()
        print("Data inserted successfully")

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    finally:
        cursor.close()
        connection.close()


@app.route('/')
def sensor_data_plot():
    global humidityColors,humidityColors_year,humidityColors_month,humidityColors_day
    try:
        weather_api()
        connection = sqlite3.connect('sensor_data.db')
        cursor = connection.cursor()

        good_threshold_humidity = list(map(int, settings['good_threshold_humidity'].split('-')))
        low_threshold_humidity = settings['low_threshold_humidity']
        high_threshold_humidity = settings['high_threshold_humidity']
        good_threshold_temp = list(map(int, settings['good_threshold_temp'].split('-')))
        low_threshold_temp = settings['low_threshold_temp']
        high_threshold_temp = settings['high_threshold_temp']


        # Get recent reading
        cursor.execute('SELECT timestamp, temperature, humidity FROM sensor_data ORDER BY timestamp DESC LIMIT 1')
        recent_reading = cursor.fetchone()
        recent_reading_time,recent_reading_temp,recent_reading_hum = recent_reading
        recent_reading_time = pytz.utc.localize(datetime.fromisoformat(recent_reading_time)).astimezone(pytz.timezone(settings['timezone'])).strftime("%Y-%m-%d %H:%M:%S")
        recent_reading_temp = round(recent_reading_temp,0)
        recent_reading_hum = round(recent_reading_hum,1)

        # All
        cursor.execute("SELECT DATE(timestamp) AS day, AVG(temperature) AS avg_temperature, AVG(humidity) AS avg_humidity FROM sensor_data GROUP BY day")
        result = cursor.fetchall()
        timestamps = [entry[0] for entry in result]
        temperature_values = [entry[1] for entry in result]
        humidity_values = [entry[2] for entry in result]
        humidityColors = ['red' if value < low_threshold_humidity or value > high_threshold_humidity else 'blue' if value >= good_threshold_humidity[0] and value <= good_threshold_humidity[1] else 'yellow' for value in humidity_values]
        tempColors = ['red' if value < low_threshold_temp or value > high_threshold_temp else 'blue' if value >= good_threshold_temp[0] and value <= good_threshold_temp[1] else 'yellow' for value in temperature_values]
        cursor.execute("SELECT DATE(timestamp) AS day, AVG(temperature) AS avg_temperature, AVG(humidity) AS avg_humidity FROM weather_api WHERE humidity IS NOT NULL GROUP BY day")
        weather_result = cursor.fetchall()
        weather_timestamps = [entry[0] for entry in weather_result]
        weather_temperature_values = [entry[1] for entry in weather_result]
        weather_humidity_values = [entry[2] for entry in weather_result]

        current_datetime = datetime.now()
        # Year
        one_year_ago = current_datetime - timedelta(days=355)
        cursor.execute("SELECT DATE(timestamp) AS day, AVG(temperature) AS avg_temperature, AVG(humidity) AS avg_humidity FROM sensor_data WHERE timestamp >= ? GROUP BY day", (one_year_ago,))
        year_result = cursor.fetchall()
        timestamps_year = [entry[0] for entry in year_result]
        temperature_values_year = [entry[1] for entry in year_result]
        humidity_values_year = [entry[2] for entry in year_result]
        humidityColors_year = ['red' if value < low_threshold_humidity or value > high_threshold_humidity else 'blue' if value >= good_threshold_humidity[0] and value <= good_threshold_humidity[1] else 'yellow' for value in humidity_values_year]
        tempColors_year = ['red' if value < low_threshold_temp or value > high_threshold_temp else 'blue' if value >= good_threshold_temp[0] and value <= good_threshold_temp[1] else 'yellow' for value in temperature_values_year]
        cursor.execute("SELECT DATE(timestamp) AS day, AVG(temperature) AS avg_temperature, AVG(humidity) AS avg_humidity FROM weather_api WHERE timestamp >= ?  AND humidity IS NOT NULL GROUP BY day", (one_year_ago,))
        weather_year = cursor.fetchall()
        weather_timestamps_year = [entry[0] for entry in weather_year]
        weather_temperature_values_year = [entry[1] for entry in weather_year]
        weather_humidity_values_year = [entry[2] for entry in weather_year]      

        # Month
        one_month_ago = current_datetime - timedelta(days=30)
        cursor.execute("SELECT DATE(timestamp) AS day, AVG(temperature) AS avg_temperature, AVG(humidity) AS avg_humidity FROM sensor_data WHERE timestamp >= ? GROUP BY day", (one_month_ago,))
        month_result = cursor.fetchall()
        timestamps_month = [entry[0] for entry in month_result]
        temperature_values_month = [entry[1] for entry in month_result]
        humidity_values_month = [entry[2] for entry in month_result]
        humidityColors_month = ['red' if value < low_threshold_humidity or value > high_threshold_humidity else 'blue' if value >= good_threshold_humidity[0] and value <= good_threshold_humidity[1] else 'yellow' for value in humidity_values_month]
        tempColors_month = ['red' if value < low_threshold_temp or value > high_threshold_temp else 'blue' if value >= good_threshold_temp[0] and value <= good_threshold_temp[1] else 'yellow' for value in temperature_values_month]
        cursor.execute("SELECT DATE(timestamp) AS day, AVG(temperature) AS avg_temperature, AVG(humidity) AS avg_humidity FROM weather_api WHERE timestamp >= ?  AND humidity IS NOT NULL GROUP BY day", (one_month_ago,))
        weather_month = cursor.fetchall()
        weather_timestamps_month = [entry[0] for entry in weather_month]
        weather_temperature_values_month = [entry[1] for entry in weather_month]
        weather_humidity_values_month = [entry[2] for entry in weather_month] 

        # Day
        one_day_ago = current_datetime - timedelta(hours=24)
        cursor.execute("SELECT timestamp, temperature, humidity FROM sensor_data WHERE timestamp >= ?", (one_day_ago,))
        day_result = cursor.fetchall()
        timestamps_day = [pytz.utc.localize(datetime.fromisoformat(entry[0])).astimezone(pytz.timezone(settings['timezone'])).strftime("%Y-%m-%d %H:%M:%S") for entry in day_result]
        temperature_values_day = [entry[1] for entry in day_result]
        humidity_values_day = [entry[2] for entry in day_result]
        humidityColors_day = ['red' if value < low_threshold_humidity or value > high_threshold_humidity else 'blue' if value >= good_threshold_humidity[0] and value <= good_threshold_humidity[1] else 'yellow' for value in humidity_values_day]
        tempColors_day = ['red' if value < low_threshold_temp or value > high_threshold_temp else 'blue' if value >= good_threshold_temp[0] and value <= good_threshold_temp[1] else 'yellow' for value in temperature_values_day]
        cursor.execute("SELECT timestamp, temperature, humidity FROM weather_api WHERE timestamp >= ? AND humidity IS NOT NULL", (one_day_ago,))
        weather_day = cursor.fetchall()
        weather_timestamps_day = [pytz.utc.localize(datetime.fromisoformat(entry[0])).astimezone(pytz.timezone(settings['timezone'])).strftime("%Y-%m-%d %H:%M:%S") for entry in weather_day]
        weather_temperature_values_day = [entry[1] for entry in weather_day]
        weather_humidity_values_day = [entry[2] for entry in weather_day] 

        return render_template('index.html', recent_reading_time=recent_reading_time, recent_reading_temp=recent_reading_temp, recent_reading_hum=recent_reading_hum, location_name = settings['location_name'],
                               data={'timestamps': timestamps, 'temperature_values': temperature_values, 'temperature_colors': tempColors,'humidity_values': humidity_values, 'humidity_colors': humidityColors},
                               data_year = {'timestamps': timestamps_year, 'temperature_values': temperature_values_year, 'temperature_colors': tempColors_year, 'humidity_values': humidity_values_year, 'humidity_colors': humidityColors_year},
                               data_month = {'timestamps': timestamps_month, 'temperature_values': temperature_values_month, 'temperature_colors': tempColors_month, 'humidity_values': humidity_values_month, 'humidity_colors': humidityColors_month},
                               data_day = {'timestamps': timestamps_day, 'temperature_values': temperature_values_day, 'temperature_colors': tempColors_day, 'humidity_values': humidity_values_day, 'humidity_colors': humidityColors_day},
                               weather_data = {'timestamps': weather_timestamps, 'temperature_values': weather_temperature_values, 'humidity_values': weather_humidity_values},
                               weather_data_year = {'timestamps': weather_timestamps_year, 'temperature_values': weather_temperature_values_year, 'humidity_values': weather_humidity_values_year},
                               weather_data_month = {'timestamps': weather_timestamps_month, 'temperature_values': weather_temperature_values_month, 'humidity_values': weather_humidity_values_month},
                               weather_data_day = {'timestamps': weather_timestamps_day, 'temperature_values': weather_temperature_values_day, 'humidity_values': weather_humidity_values_day})

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    finally:
        cursor.close()
        connection.close()

## Default settings
settings = {
    'timezone': 'US/Eastern',
    'good_threshold_humidity': '45-55',
    'low_threshold_humidity': 30,
    'high_threshold_humidity': 60,
    'good_threshold_temp': '50-65',
    'low_threshold_temp': 32,
    'high_threshold_temp': 80,
    'location_name': 'Location 1'
}

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    if request.method == 'GET':
        return render_template('settings.html', settings=settings)
    elif request.method == 'POST':
        update_settings(request.form)
        return redirect(url_for('sensor_data_plot'))

def update_settings(form_data):
    settings['location_name'] = form_data['location_name']
    settings['timezone'] = form_data['timezone']
    settings['good_threshold_humidity'] = form_data['good_threshold_humidity']
    settings['low_threshold_humidity'] = int(form_data['low_threshold_humidity'])
    settings['high_threshold_humidity'] = int(form_data['high_threshold_humidity'])
    settings['good_threshold_temp'] = form_data['good_threshold_temp']
    settings['low_threshold_temp'] = int(form_data['low_threshold_temp'])
    settings['high_threshold_temp'] = int(form_data['high_threshold_temp'])

def send_email():
    print('Preparing to send email')
    try:
        connection = sqlite3.connect('sensor_data.db')
        cursor = connection.cursor()
        one_day_ago = datetime.now() - timedelta(hours=24)
        cursor.execute("SELECT AVG(humidity) FROM sensor_data WHERE timestamp >= ?", (one_day_ago,))
        avg_hum = cursor.fetchone()[0]

        if avg_hum > settings['high_threshold_humidity'] or avg_hum < settings['low_threshold_humidity']:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            body = f'Your crawlspace needs to be checked! The humidity at {settings["location_name"]} from the last 24 hours was {avg_hum}'
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(smtp_server, smtp_port) as smtp:
                smtp.starttls()
                smtp.login(smtp_username, smtp_password)
                smtp.send_message(msg)
            
            print('Email sent')
            return True
        else:
            print('Humidity within normal range, no email sent')
            return False

    except Exception as e:
        print(f'Error sending email: {e}')
        return False
    finally:
        cursor.close()
        connection.close()

@app.route('/publish-mqtt', methods=['POST'])
def publish_mqtt():
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "request": "request sent",
            "time": current_time
        }
        json_payload = json.dumps(payload)
        result = client.publish(MQTT_REQUEST_TOPIC, json_payload)
        status = result[0]
        if status == 0:
            print(f"Sent request to request topic!")
        else:
            print(f"Failed to send message to request topic")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-latest-readings', methods=['GET'])
def get_latest_readings():
    try:
        connection = sqlite3.connect('sensor_data.db')
        cursor = connection.cursor()
        cursor.execute('SELECT timestamp, temperature, humidity FROM sensor_data ORDER BY timestamp DESC LIMIT 1')
        latest_reading = cursor.fetchone()

        if latest_reading:
            latest_reading_time, latest_reading_temp, latest_reading_hum = latest_reading
            latest_reading_time = pytz.utc.localize(datetime.fromisoformat(latest_reading_time)).astimezone(pytz.timezone(settings['timezone'])).strftime("%Y-%m-%d %H:%M:%S")
            return jsonify({
                'success': True,
                'readings': {
                    'timestamp': latest_reading_time,
                    'temperature': round(latest_reading_temp,0),
                    'humidity': round(latest_reading_hum,1)
                }
            })
        else:
            return jsonify({'success': False, 'error': 'No readings available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def weather_api():
    connection = sqlite3.connect('sensor_data.db')
    cursor = connection.cursor()
    g = geocoder.ip('me')
    url = "https://api.open-meteo.com/v1/forecast"
    cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)
    params = {
        "latitude": g.latlng[0],
        "longitude": g.latlng[1],
        "current": ["temperature_2m", "relative_humidity_2m"]
    }
    responses = openmeteo.weather_api(url, params=params)

    response = responses[0]
    current = response.Current()
    current_temperature_2m = current.Variables(0).Value()
    current_relative_humidity_2m = current.Variables(1).Value()
    cursor.execute(
        'INSERT INTO weather_api (timestamp, temperature, humidity) VALUES (?, ?, ?)',
        (current.Time(), current_temperature_2m, current_relative_humidity_2m)
    )
    print("Weather API data inserted successfully")
    cursor.close()
    connection.close()

client = mqtt.Client(protocol=mqtt.MQTTv5)
client.tls_set(
    MQTT_CA_PATH,
    certfile=MQTT_CERT_PATH,
    keyfile=MQTT_KEY_PATH,
    tls_version=2,
)
client.on_connect = on_connect
client.on_message = on_message

def mqtt_thread_function():
    client.connect(MQTT_BROKER, port=MQTT_PORT, keepalive=60)
    print('Connected to client')
    client.loop_forever()

mqtt_thread = threading.Thread(target=mqtt_thread_function)

if __name__ == '__main__':
    mqtt_thread.start()
    app.run(host = '0.0.0.0', port = 80, debug = False)