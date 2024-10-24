# Data Collection and Preprocessing
# Collect historical trade data, clean it, and prepare it for analysis.

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# Load the historical data
data = pd.read_csv('crypto_data.csv')  # Assume we have a CSV with historical data

# Convert timestamp to datetime
data['timestamp'] = pd.to_datetime(data['timestamp'])

# Sort data by timestamp
data = data.sort_values(by='timestamp')

# Feature Engineering
data['hour'] = data['timestamp'].dt.hour
data['day_of_week'] = data['timestamp'].dt.dayofweek

# Select relevant features
features = ['price', 'volume', 'hour', 'day_of_week']
target = 'price'

# Scale the data
scaler = MinMaxScaler()
data[features] = scaler.fit_transform(data[features])

# Create sequences for time series forecasting
def create_sequences(data, seq_length):
    xs, ys = [], []
    for i in range(len(data) - seq_length):
        x = data.iloc[i:(i + seq_length)][features].values
        y = data.iloc[i + seq_length][target]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

seq_length = 60  # Use the last 60 minutes for prediction
X, y = create_sequences(data, seq_length)


# Model Building
# Use a sophisticated model like LSTM (Long Short-Term Memory) for time series prediction.

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# Build the LSTM model
model = Sequential()
model.add(LSTM(100, return_sequences=True, input_shape=(seq_length, len(features))))
model.add(Dropout(0.2))
model.add(LSTM(100, return_sequences=False))
model.add(Dropout(0.2))
model.add(Dense(1))

model.compile(optimizer='adam', loss='mean_squared_error')

# Train the model
history = model.fit(X, y, epochs=50, batch_size=64, validation_split=0.2)

# Save the model
model.save('crypto_price_predictor.h5')


# Prediction Generation
# Use the trained model to generate predictions and send them to Kafka.

import random
from kafka import KafkaProducer
import json
import logging

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Load the trained model
model = tf.keras.models.load_model('crypto_price_predictor.h5')

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Generate predictions based on the latest trade data
def generate_prediction():
    """Generates crypto prediction data based on the latest trade data."""
    for symbol, data in latest_trade_data.items():
        # Prepare the data for prediction
        recent_data = data['history'][-seq_length:]
        recent_data = scaler.transform(recent_data)
        recent_data = np.array([recent_data])

        # Make the prediction
        prediction = model.predict(recent_data)[0][0]
        prediction = scaler.inverse_transform([[prediction]])[0][0]

        record = {
            'symbol': symbol,
            'time': data['timestamp'],
            'close': data['price'],
            'prediction': prediction
        }

        logger.info(f"Generated prediction: {record}")
        try:
            future = producer.send(kafka_topic_predictions, key=symbol.encode('utf-8'), value=record)
            future.add_callback(delivery_report)
            future.add_errback(lambda exc: logger.error(f"Failed to send prediction to Kafka: {exc}"))
        except Exception as e:
            logger.error(f"Failed to send prediction to Kafka: {e}")

def delivery_report(record_metadata):
    logger.info(f"Message delivered to {record_metadata.topic} [{record_metadata.partition}] at offset {record_metadata.offset}")

# Mockup latest trade data for testing
latest_trade_data = {
    'BTC': {
        'timestamp': '2024-08-05T12:00:00Z',
        'price': 30000,
        'history': data.tail(seq_length)[features].values.tolist()
    }
}

# Run prediction
generate_prediction()
