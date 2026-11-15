import json
import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import paho.mqtt.client as mqtt

from ml_engine import MLPredictor

BROKER = "mosquitto"
PORT = 1883
TOPIC = "iot/pm25"

TARGET_RECORDS = 8706

records = []


def process_data():

    print("Processing PM2.5 dataset...")

    df = pd.DataFrame(records)

    print(f"Collected records: {len(df)}")

    # Remove duplicates
    df = df.drop_duplicates()

    # Sort timestamps
    df = df.sort_values("Timestamp")

    print(f"After deduplication: {len(df)}")

    # Coursework validation
    print("\nLast two values:")

    if len(df) >= 2:
        print(df.tail(2))

    # Convert timestamp
    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        unit="ms"
    )

    # Print timestamp + value
    print("\nFormatted PM2.5 data")

    for _, row in df.iterrows():
        print(
            f"{row['Timestamp']}  {row['Value']}"
        )

    # 10 minute average
    averaged = (
        df.set_index("Timestamp")
          .resample("10min")
          .mean(numeric_only=True)
          .reset_index()
    )

    print("\nAveraged dataset")
    print(averaged.head())

    # Historical graph
    plt.figure(figsize=(12, 6))

    plt.plot(
        averaged["Timestamp"],
        averaged["Value"]
    )

    plt.title("Average PM2.5")
    plt.xlabel("Time")
    plt.ylabel("PM2.5")

    plt.tight_layout()

    plt.savefig(
        "/output/pm25_history.png"
    )

    plt.close()

    # Prophet prediction
    predictor = MLPredictor(
        averaged.copy()
    )

    predictor.train()

    forecast = predictor.predict()

    forecast_fig = predictor.plot_result(
        forecast
    )

    forecast_fig.savefig(
        "/output/pm25_forecast.png"
    )

    print(
        "Saved: /output/pm25_history.png"
    )

    print(
        "Saved: /output/pm25_forecast.png"
    )


def on_message(client, userdata, msg):

    global records

    try:

        data = json.loads(
            msg.payload.decode()
        )

        records.append(
            {
                "Timestamp": data["Timestamp"],
                "Value": float(data["Value"])
            }
        )

        if len(records) % 100 == 0:
            print(
                f"Collected {len(records)} records",
                flush=True
            )

        if len(records) >= TARGET_RECORDS:

            client.loop_stop()

            process_data()

    except Exception as error:

        print(
            f"Error: {error}",
            flush=True
        )


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="pm25-predictor"
)

client.on_message = on_message

client.connect(
    BROKER,
    PORT,
    60
)

client.subscribe(TOPIC)

print(
    "Collecting PM2.5 data...",
    flush=True
)

client.loop_forever()
