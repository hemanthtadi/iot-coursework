import json

import paho.mqtt.client as mqtt
import requests

BROKER = "mosquitto"
PORT = 1883

VEHICLE_TOPIC = "iot/vehicle_count"
IMAGE_TOPIC = "iot/annotated_image"
QUALITY_TOPIC = "iot/air_quality"

DASHBOARD_URL = "http://dashboard.cloud.ncl.ac.uk:8000/api/records"

latest_image = None
latest_quality = None


def send_to_dashboard():

    global latest_image
    global latest_quality

    if latest_image is None:
        print("Skipping: image missing")
        return

    if latest_quality is None:
        print("Skipping: PM2.5 result missing")
        return

    data = {
        "timestamp": int(
            latest_quality["Timestamp"] / 1000
        ),
        "value": latest_quality["Value"],
        "predicted_quality":
            latest_quality["Quality"]
    }

    files = {
        "image": (
            "annotated.jpg",
            latest_image,
            "image/jpeg"
        )
    }

    try:

        print(
            "DATA:",
            data,
            flush=True
        )

        response = requests.post(
            DASHBOARD_URL,
            data=data,
            files=files,
            timeout=30
        )

        print(
            f"Dashboard Response {response.status_code}",
            flush=True
        )

        print(
            f"Response Body: {response.text}",
            flush=True
        )

    except Exception as error:

        print(
            f"Dashboard Error: {error}",
            flush=True
        )


def on_message(client, userdata, msg):

    global latest_image
    global latest_quality

    if msg.topic == IMAGE_TOPIC:

        latest_image = msg.payload

    elif msg.topic == QUALITY_TOPIC:

        latest_quality = json.loads(
            msg.payload.decode()
        )

    elif msg.topic == VEHICLE_TOPIC:

        data = json.loads(
            msg.payload.decode()
        )

        vehicle_count = int(
            data["vehicle_count"]
        )

        print(
            f"Vehicle Count: {vehicle_count}",
            flush=True
        )

        if vehicle_count > 5:

            send_to_dashboard()


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="decision-module"
)

client.on_message = on_message

client.connect(
    BROKER,
    PORT,
    60
)

client.subscribe(VEHICLE_TOPIC)
client.subscribe(IMAGE_TOPIC)
client.subscribe(QUALITY_TOPIC)

print(
    "Decision Module Started",
    flush=True
)

client.loop_forever()
