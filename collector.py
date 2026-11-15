import json
import time
import requests
import paho.mqtt.client as mqtt

SENSOR_URL = "http://smartcam.uo.ncl.ac.uk:8001/sensor"
CAMERA_URL = "http://smartcam.uo.ncl.ac.uk:8001/camera"

MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883

SENSOR_TOPIC = "iot/pm25"
CAMERA_TOPIC = "iot/camera"

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="iot-data-collector"
)

def connect_mqtt():
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start()
            print("Connected to Mosquitto", flush=True)
            return
        except Exception as error:
            print(f"MQTT connection failed: {error}", flush=True)
            time.sleep(5)

def collect_sensor_data():
    try:
        response = requests.get(SENSOR_URL, timeout=20)
        response.raise_for_status()
        readings = response.json()

        for reading in readings:
            variable = reading.get("Variable", "").strip().upper()

            # Accept PM2.5 naming variations.
            if variable not in ("PM2.5", "PM25", "PM 2.5"):
                continue

            timestamp = reading.get("Timestamp")
            value = reading.get("Value")

            if timestamp is None or value is None:
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            if value > 50:
                print(
                    f"OUTLIER: Timestamp={timestamp}, Value={value}",
                    flush=True
                )
                continue

            message = {
                "Timestamp": timestamp,
                "Value": value
            }

            client.publish(
                SENSOR_TOPIC,
                json.dumps(message),
                qos=1
            )

            print(f"Published PM2.5: {message}", flush=True)

    except Exception as error:
        print(f"Sensor collection error: {error}", flush=True)

def collect_camera_frame():
    try:
        response = requests.get(CAMERA_URL, timeout=20)
        response.raise_for_status()

        # Split the JPEG into chunks to avoid oversized MQTT messages.
        frame = response.content
        chunk_size = 64 * 1024
        frame_id = str(time.time_ns())
        total_chunks = (len(frame) + chunk_size - 1) // chunk_size

        for index in range(total_chunks):
            chunk = frame[index * chunk_size:(index + 1) * chunk_size]

            metadata = {
                "frame_id": frame_id,
                "chunk_index": index,
                "total_chunks": total_chunks,
                "data": chunk.hex()
            }

            client.publish(
                CAMERA_TOPIC,
                json.dumps(metadata),
                qos=1
            )

        print(
            f"Published camera frame: {len(frame)} bytes "
            f"in {total_chunks} chunks",
            flush=True
        )

    except Exception as error:
        print(f"Camera collection error: {error}", flush=True)

def main():
    connect_mqtt()

    while True:
        collect_sensor_data()
        collect_camera_frame()
        time.sleep(5)

if __name__ == "__main__":
    main()
