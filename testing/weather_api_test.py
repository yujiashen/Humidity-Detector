import openmeteo_requests

import requests_cache
import pandas as pd
from retry_requests import retry
import datetime
import timedelta
import geocoder
import sqlite3

connection = sqlite3.connect('sensor_data.db')
cursor = connection.cursor()

def fetch_weather_api():
    g = geocoder.ip('me')
    print(g.latlng)
    today = datetime.date.today()
    cursor.execute("SELECT DATE(MIN(timestamp)) FROM sensor_data")
    first_date = cursor.fetchone()[0]
    print(first_date)
    cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": g.latlng[0],
        "longitude": g.latlng[1],
        "start_date": first_date,
        "end_date": datetime.date.today(),
        "hourly": ["temperature_2m", "relative_humidity_2m"],
        "temperature_unit": "fahrenheit"
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates {response.Latitude()}°E {response.Longitude()}°N")
    print(f"Elevation {response.Elevation()} m asl")
    print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()

    hourly_data = {"timestamp": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s"),
        end = pd.to_datetime(hourly.TimeEnd(), unit = "s"),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}
    hourly_data["temperature"] = hourly_temperature_2m
    hourly_data["humidity"] = hourly_relative_humidity_2m

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    # print(hourly_dataframe)
    # Save the data to the weather_api table (create the table if it doesn't exist)
    hourly_dataframe.to_sql('weather_api', connection, if_exists='replace', index=False)
    cursor.execute("SELECT * FROM weather_api")
    result = cursor.fetchall()
    print(result)

fetch_weather_api()