import uuid
from kafka.admin import KafkaAdminClient, NewTopic

def delete_topic(topic_name):
    admin_client = KafkaAdminClient(
        bootstrap_servers="localhost:9092",  # Update with your server configuration
        client_id=str(uuid.uuid4())
    )
    admin_client.delete_topics([topic_name])
    print(f"Topic {topic_name} deleted.")

    admin_client.close()

# Example usage
delete_topic("default-topic")