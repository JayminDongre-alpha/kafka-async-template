"""
Simple Kafka Publisher Example
"""
from kafka import KafkaProducer
import json
import time
from datetime import datetime

def create_producer():
    """Create a Kafka producer instance"""
    return KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )

def publish_message(producer, topic, message):
    """Publish a message to the specified topic"""
    try:
        # Add timestamp to message
        message['timestamp'] = datetime.now().isoformat()

        # Send the message
        future = producer.send(topic, value=message)

        # Wait for the message to be sent
        record_metadata = future.get(timeout=10)

        print(f"Message published successfully:")
        print(f"Topic: {record_metadata.topic}")
        print(f"Partition: {record_metadata.partition}")
        print(f"Offset: {record_metadata.offset}")
        print(f"Message: {message}")
        print("-------------------")

    except Exception as e:
        print(f"Error publishing message: {str(e)}")

def main():
    # Create producer instance
    producer = create_producer()

    # Define the topic
    topic = 'test-topic'

    try:
        # Publish some sample messages
        message_id = 0
        while True:
            message = {
                'id': message_id,
                'message': f'Test message {message_id}',
                'value': message_id * 100
            }

            publish_message(producer, topic, message)
            message_id += 1

            # Wait for 2 seconds before sending next message
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nStopping publisher...")
    finally:
        # Clean up resources
        producer.close()
        print("Publisher stopped")

if __name__ == "__main__":
    main()