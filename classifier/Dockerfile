FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY classifier.py .
COPY air_quality_model.tflite .

CMD ["python", "-u", "classifier.py"]
