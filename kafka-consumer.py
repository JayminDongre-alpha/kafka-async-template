"""
Simple Kafka Subscriber Example
"""
from kafka import KafkaConsumer
import json


def create_consumer(topic):
    """Create a Kafka consumer instance"""
    return KafkaConsumer(
        topic,
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='earliest',  # Start reading from beginning of topic
        enable_auto_commit=True,  # Automatically commit offsets
        group_id='my-group',  # Consumer group ID
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )


def process_message(message):
    """Process the received message"""
    print(f"Received message:")
    print(f"Topic: {message.topic}")
    print(f"Partition: {message.partition}")
    print(f"Offset: {message.offset}")
    print(f"Timestamp: {message.timestamp}")
    print(f"Message: {message.value}")
    print("-------------------")


def main():
    # Define the topic
    topic = 'test-topic'

    # Create consumer instance
    print(f"Starting consumer for topic: {topic}")
    consumer = create_consumer(topic)

    try:
        # Continuously poll for new messages
        for message in consumer:
            process_message(message)

    except KeyboardInterrupt:
        print("\nStopping consumer...")
    finally:
        # Clean up resources
        consumer.close()
        print("Consumer stopped")


if __name__ == "__main__":
    main()