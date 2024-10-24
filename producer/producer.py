import websocket
import json
import time
import schedule
from kafka import KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from datetime import datetime
import random
import config
import logging
import threading
from collections import deque
from itertools import islice
from ratelimit import limits, sleep_and_retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
c = config.load_config()

kafka_bootstrap_server = c.KAFKA_BOOTSTRAP_SERVER
kafka_topic_data = c.KAFKA_TOPIC_DATA
kafka_topic_predictions = c.KAFKA_TOPIC_PREDICTIONS
symbols = c.crypto_SYMBOLS
interval = c.PRODUCER_INTERVAL_SECONDS
finnhub_api_key = c.FINNHUB_API_KEY

# Initialize latest_trade_data
latest_trade_data = {}
message_queue = deque()  # Use a deque to store messages

# Function to create Kafka topics if they don't exist
def create_kafka_topics():
    try:
        client = KafkaAdminClient(bootstrap_servers=kafka_bootstrap_server)
        topics = [kafka_topic_data, kafka_topic_predictions]
        new_topics = [NewTopic(name=topic, num_partitions=1, replication_factor=1) for topic in topics]
        existing_topics = client.list_topics()

        topics_to_create = [topic for topic in new_topics if topic.name not in existing_topics]
        if topics_to_create:
            client.create_topics(new_topics=topics_to_create)
            logger.info(f"Topics {', '.join([topic.name for topic in topics_to_create])} created")
        else:
            logger.info("No new topics to create. All topics already exist.")
    except Exception as e:
        logger.error(f"An error occurred while creating Kafka topics: {e}")
    finally:
        client.close()
        logger.info("Kafka client closed.")

# Kafka Producer initialization with retry logic
def create_producer(bootstrap_servers):
    attempts = 0
    while attempts < 5:
        try:
            producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                                     value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                                     key_serializer=lambda k: k.encode('utf-8'))
            logger.info("Kafka producer created successfully")
            return producer
        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            attempts += 1
            time.sleep(2 ** attempts)  # Exponential backoff
    raise Exception("Failed to create Kafka producer after several attempts")

producer = create_producer(kafka_bootstrap_server)

def delivery_report(record_metadata):
    logger.info(f"Message delivered to {record_metadata.topic} [{record_metadata.partition}]")

@sleep_and_retry
@limits(calls=30, period=1)  # Adjust limits as per the API documentation
def send_websocket_message(ws, message):
    """Send a message via WebSocket with rate limiting."""
    ws.send(message)

def on_message(ws, message):
    """Callback function to handle incoming WebSocket messages."""
    logger.info(f"WebSocket message received: {message}")
    data = json.loads(message)
    if data.get('type') == 'trade':
        for trade in data['data']:
            symbol = trade['s']
            record = {
                'symbol': symbol,
                'timestamp': datetime.fromtimestamp(trade['t'] / 1000.0).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'price': trade['p'],
                'volume': trade['v']
            }
            latest_trade_data[symbol] = record  # Update latest trade data
            message_queue.append((symbol, record))  # Add to the message queue
            logger.info(f"Queued trade data: {record}")

def on_error(ws, error):
    """Callback function to handle WebSocket errors."""
    logger.error(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Callback function to handle WebSocket closure."""
    logger.info(f"### closed ### status: {close_status_code}, message: {close_msg}")
    reconnect_websocket()

def reconnect_websocket():
    """Recreate and start the WebSocket connection with exponential backoff."""
    global ws_thread, ws
    logger.info("Reconnecting to WebSocket...")
    try:
        ws.close()
        ws_thread.join()  # Ensure previous thread is finished
    except Exception as e:
        logger.error(f"Error closing previous WebSocket connection: {e}")

    reconnect_delay = 5
    while True:
        try:
            time.sleep(reconnect_delay)
            ws = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={finnhub_api_key}",
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.on_open = on_open

            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.start()
            break
        except Exception as e:
            logger.error(f"Error during reconnection: {e}")
            reconnect_delay = min(reconnect_delay * 2, 60)  # Increase delay up to 60 seconds

def on_open(ws):
    """Callback function to handle WebSocket connection opening."""
    for symbol in symbols:
        send_websocket_message(ws, json.dumps({'type': 'subscribe', 'symbol': symbol}))
    logger.info(f"Subscribed to symbols: {symbols}")

def generate_prediction():
    """Generates crypto prediction data based on the latest trade data."""
    for symbol, data in latest_trade_data.items():
        last_price = data['price']
        prediction = last_price * (1 + random.uniform(-0.02, 0.02))  # Simple prediction logic
        record = {
            'symbol': symbol,
            'time': data['timestamp'],
            'close': last_price,
            'prediction': prediction
        }
        logger.info(f"Generated prediction: {record}")
        try:
            future = producer.send(kafka_topic_predictions, key=symbol, value=record)
            future.add_callback(delivery_report)
            future.add_errback(lambda exc: logger.error(f"Failed to send prediction to Kafka: {exc}"))
        except Exception as e:
            logger.error(f"Failed to send prediction to Kafka: {e}")

def send_batch_messages():
    """Send a batch of messages from the queue to Kafka."""
    batch_size = 90  # Set the batch size according to your needs
    while message_queue:
        batch = list(islice(message_queue, batch_size))
        for symbol, record in batch:
            try:
                future = producer.send(kafka_topic_data, key=symbol, value=record)
                future.add_callback(delivery_report)
                future.add_errback(lambda exc: logger.error(f"Failed to send record to Kafka: {exc}"))
            except Exception as e:
                logger.error(f"Failed to send record to Kafka: {e}")
        for _ in range(len(batch)):
            message_queue.popleft()  # Remove the sent messages from the queue

def job():
    """Job to generate predictions."""
    generate_prediction()

if __name__ == "__main__":
    # Ensure Kafka topics are created
    create_kafka_topics()

    # Initialize the WebSocket connection
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={finnhub_api_key}",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open

    # Schedule the prediction job
    schedule.every(interval).seconds.do(job)
    schedule.every(3).seconds.do(send_batch_messages)  # Adjust the interval as needed

    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.start()

    # Run the scheduled jobs in the main thread
    try:
        while True:
            schedule.run_pending()
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    finally:
        producer.flush()
        ws.close()
        ws_thread.join()
        logger.info("Producer and WebSocket connection closed.")
