# Humidity-Detector

The humidity detector is a specialized IoT solution tailored to address humidity-related issues in challenging, hard-to-reach spaces, particularly crawlspaces and basements. Powered by the ESP32 microcontroller and DHT22 sensor, it provides accurate humidity measurements for crawlspaces, preventing problems like mold growth. The application provides homeowners with real-time and historical humidity data, automated alerts, and on-demand readings, offering a user-friendly interface for proactive management of crawl space health. This project emerged out of a desire to solve common problems caused by excessive humidity, giving homeowners real-time insights for proactive crawlspace monitoring.

## Technology Stack
- **Microcontroller:** ESP32
- **Sensor:** DHT22
- **IoT Communication:** AWS IoT Core
- **Backend:** Flask
- **Database:** MySQL
- **Deployment:** Amazon Lightsail (Virtual Cloud Server)

## Device Setup
1. Update the `secrets.h` file on the device with your WiFi network and AWS IoT credentials.
2. Upload the `final_project.ino` file onto the device.

## Application Setup
1. **Register a Thing on AWS IoT Core**
2. Download key files from AWS console. Obtain `MQTT_BROKER` information and replace values in the MQTT configuration section of `main.py`.
3. Configure email information in `main.py`.
4. Set up an AWS Lightsail instance.
5. In the server, use SCP to transfer the application files and your key files into the instance.
6. Install Python3 and Pip. Run the following command to install dependencies:

    ```bash
    pip install flask plotly paho-mqtt mysql-connector-python sqlite3 random smtplib email threading pytz geocoder openmeteo_requests requests_cache retry_requests
    ```

7. Execute the following command to start the Flask app in the background:

    ```bash
    sudo nohup python main.py > log.txt 2>&1 &
    ```

The app should now be running in the background! Access the app using the static public IP found on Lightsail.

## Files
### Device Files:
- `detector_device.ino`
- `secrets.h`

### Application Files:
- `main.py`
- `index.html`
- `settings.html`

### Test Files:
- `weather_api_test.py`
- `fake_table.py`
