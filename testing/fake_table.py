import sqlite3
from random import uniform
from datetime import datetime, timedelta
conn = sqlite3.connect('sensor_data.db')
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS sensor_data;")
print("Deleted existing sensor_data table.")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id VARCHAR(255),
        humidity FLOAT,
        temperature FLOAT,
        timestamp TIMESTAMP
    )
''')

# Insert 8760 rows of data
start_date = datetime(2022, 12, 7)
for i in range(8760):
    device_id = 'ESP32'
    humidity = round(uniform(20, 80), 2)
    temperature = round(uniform(40, 90), 2)
    timestamp = start_date + timedelta(hours=i)
    cursor.execute('''
        INSERT INTO sensor_data (device_id, humidity, temperature, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (device_id, humidity, temperature, timestamp))
conn.commit()
cursor.execute('SELECT timestamp, humidity, temperature FROM sensor_data')
data = cursor.fetchall()
timestamps, humidities, temperatures = zip(*data)
conn.close()
