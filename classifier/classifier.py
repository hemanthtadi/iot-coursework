import json
import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import paho.mqtt.client as mqtt
import tensorflow as tf

BROKER = "mosquitto"
PORT = 1883

INPUT_TOPIC = "iot/pm25"
OUTPUT_TOPIC = "iot/air_quality"

MODEL_PATH = "air_quality_model.tflite"

records = []

interpreter = tf.lite.Interpreter(
    model_path=MODEL_PATH
)

interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

labels = [
    "GREEN",
    "RED",
    "YELLOW"
]


def classify(value):

    input_data = np.array(
        [[value]],
        dtype=np.float32
    )

    interpreter.set_tensor(
        input_details[0]["index"],
        input_data
    )

    interpreter.invoke()

    prediction = interpreter.get_tensor(
        output_details[0]["index"]
    )

    index = np.argmax(prediction)

    return labels[index]


def generate_graphs():

    if len(records) < 10:
        return

    df = pd.DataFrame(records)

    counts = (
        df["Quality"]
        .value_counts()
    )

    plt.figure(figsize=(6, 4))

    counts.plot(kind="bar")

    plt.title("Air Quality Counts")

    plt.savefig(
        "/output/classification_counts.png"
    )

    plt.close()

    plt.figure(figsize=(12, 5))

    colour_map = {
        "GREEN": "green",
        "YELLOW": "orange",
        "RED": "red"
    }

    for quality in colour_map:

        subset = df[
            df["Quality"] == quality
        ]

        plt.scatter(
            subset.index,
            subset["Value"],
            c=colour_map[quality],
            label=quality
        )

    plt.legend()

    plt.savefig(
        "/output/time_series_classification.png"
    )

    plt.close()

    plt.figure(figsize=(8, 5))

    plt.hist(
        df["Value"],
        bins=20
    )

    plt.title(
        "PM2.5 Distribution"
    )

    plt.savefig(
        "/output/pm25_distribution.png"
    )

    plt.close()

    summary = open(
        "/output/classification_summary.txt",
        "w"
    )

    summary.write(
        str(counts)
    )

    summary.close()


def on_message(client, userdata, msg):

    payload = json.loads(
        msg.payload.decode()
    )

    value = float(
        payload["Value"]
    )

    quality = classify(value)

    print(
        f"PM2.5={value} => {quality}",
        flush=True
    )

    output = {
        "Timestamp": payload["Timestamp"],
        "Value": value,
        "Quality": quality
    }

    client.publish(
        OUTPUT_TOPIC,
        json.dumps(output),
        qos=1
    )

    records.append(output)

    if len(records) % 100 == 0:
        generate_graphs()


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="air-quality-classifier"
)

client.on_message = on_message

client.connect(
    BROKER,
    PORT,
    60
)

client.subscribe(
    INPUT_TOPIC
)

print(
    "Classifier waiting for PM2.5 data...",
    flush=True
)

client.loop_forever()
