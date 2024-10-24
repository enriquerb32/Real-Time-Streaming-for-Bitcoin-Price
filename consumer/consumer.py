from kafka import KafkaConsumer
import json
import config

# Load configuration
c = config.load_config()

kafka_bootstrap_server = c.KAFKA_BOOTSTRAP_SERVER
kafka_topic_data = c.KAFKA_TOPIC_DATA
kafka_topic_predictions = c.KAFKA_TOPIC_PREDICTIONS

def consume_messages(topic):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=kafka_bootstrap_server,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='my-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    for message in consumer:
        print(f"Received message from {topic}: {message.value}")

if __name__ == "__main__":
    import threading

    # Start a thread to consume messages from kafka_topic_data
    data_thread = threading.Thread(target=consume_messages, args=(kafka_topic_data,))
    data_thread.start()

    # Start a thread to consume messages from kafka_topic_predictions
    predictions_thread = threading.Thread(target=consume_messages, args=(kafka_topic_predictions,))
    predictions_thread.start()

    # Join threads
    data_thread.join()
    predictions_thread.join()
