import json
import cv2
import numpy as np
import paho.mqtt.client as mqtt
from ultralytics import YOLO

BROKER = "mosquitto"
PORT = 1883

CAMERA_TOPIC = "iot/camera"

COUNT_TOPIC = "iot/vehicle_count"
IMAGE_TOPIC = "iot/annotated_image"

model = YOLO("yolov8n.pt")

frame_chunks = {}

VEHICLE_CLASSES = {
    2,   # car
    3,   # motorcycle
    5,   # bus
    7    # truck
}


def process_frame(image_bytes):

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    results = model(image)

    vehicle_count = 0

    for result in results:

        for box in result.boxes:

            cls = int(box.cls[0])

            if cls in VEHICLE_CLASSES:

                vehicle_count += 1

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                cv2.rectangle(
                    image,
                    (x1, y1),
                    (x2, y2),
                    (0, 0, 255),
                    2
                )

    count_message = {
        "vehicle_count": vehicle_count
    }

    client.publish(
        COUNT_TOPIC,
        json.dumps(count_message),
        qos=1
    )

    success, encoded = cv2.imencode(
        ".jpg",
        image
    )

    if success:

        client.publish(
            IMAGE_TOPIC,
            encoded.tobytes(),
            qos=1
        )

    print(
        f"Detected {vehicle_count} vehicles",
        flush=True
    )


def on_message(client, userdata, msg):

    payload = json.loads(
        msg.payload.decode()
    )

    frame_id = payload["frame_id"]

    if frame_id not in frame_chunks:
        frame_chunks[frame_id] = {}

    frame_chunks[frame_id][
        payload["chunk_index"]
    ] = bytes.fromhex(
        payload["data"]
    )

    total_chunks = payload["total_chunks"]

    if len(frame_chunks[frame_id]) == total_chunks:

        image_bytes = b''

        for i in range(total_chunks):
            image_bytes += frame_chunks[
                frame_id
            ][i]

        del frame_chunks[frame_id]

        process_frame(image_bytes)


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="yolo-detector"
)

client.on_message = on_message

client.connect(
    BROKER,
    PORT,
    60
)

client.subscribe(CAMERA_TOPIC)

print(
    "Waiting for camera frames...",
    flush=True
)

client.loop_forever()
