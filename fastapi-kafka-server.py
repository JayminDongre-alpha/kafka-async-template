"""
FastAPI WebSocket Server with Topic Selection and Separate Kafka Managers
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import asyncio
import logging
from typing import Dict, Set
import uvicorn
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kafka WebSocket Bridge")

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

@dataclass
class KafkaPublisherManager:
    """Manages Kafka producer per WebSocket client"""
    client_id: str
    topic: str
    producer: AIOKafkaProducer = None

    async def setup(self):
        """Initialize Kafka producer"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        logger.info(f"Kafka producer started for client {self.client_id} on topic {self.topic}")

    async def publish_message(self, message):
        """Publish message to Kafka"""
        if self.producer:
            await self.producer.send_and_wait(self.topic, value=message)
            logger.info(f"Message published to Kafka topic {self.topic} for client {self.client_id}")

    async def cleanup(self):
        """Cleanup Kafka resources"""
        if self.producer:
            await self.producer.stop()
            logger.info(f"Kafka producer stopped for client {self.client_id}")

@dataclass
class KafkaConsumerManager:
    """Manages Kafka consumer per WebSocket client"""
    client_id: str
    topic: str
    consumer: AIOKafkaConsumer = None
    consumer_task: asyncio.Task = None

    async def setup(self, message_handler):
        """Initialize Kafka consumer"""
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=f"websocket_group_{self.client_id}",
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest'
        )
        await self.consumer.start()
        self.consumer_task = asyncio.create_task(self._consume_messages(message_handler))
        logger.info(f"Kafka consumer started for client {self.client_id} on topic {self.topic}")

    async def _consume_messages(self, message_handler):
        """Consume messages from Kafka"""
        try:
            async for message in self.consumer:
                await message_handler(json.dumps(message.value))
        except asyncio.CancelledError:
            logger.info(f"Consumer task cancelled for client {self.client_id}")
        except Exception as e:
            logger.error(f"Error in consumer task for client {self.client_id}: {e}")

    async def cleanup(self):
        """Cleanup Kafka resources"""
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass

        if self.consumer:
            await self.consumer.stop()
            logger.info(f"Kafka consumer stopped for client {self.client_id}")

class ConnectionManager:
    def __init__(self):
        self.publishers: Dict[WebSocket, KafkaPublisherManager] = {}
        self.consumers: Dict[WebSocket, KafkaConsumerManager] = {}

    async def connect_publisher(self, websocket: WebSocket, client_id: str, topic: str):
        """Connect publisher and initialize Kafka producer"""
        await websocket.accept()
        manager = KafkaPublisherManager(client_id=client_id, topic=topic)
        await manager.setup()
        self.publishers[websocket] = manager
        logger.info(f"Publisher connected. Total publishers: {len(self.publishers)}")

    async def connect_subscriber(self, websocket: WebSocket, client_id: str, topic: str):
        """Connect subscriber and initialize Kafka consumer"""
        await websocket.accept()
        manager = KafkaConsumerManager(client_id=client_id, topic=topic)
        await manager.setup(
            message_handler=lambda msg: websocket.send_text(msg)
        )
        self.consumers[websocket] = manager
        logger.info(f"Subscriber connected. Total consumers: {len(self.consumers)}")

    async def disconnect_publisher(self, websocket: WebSocket):
        """Disconnect publisher and cleanup resources"""
        if websocket in self.publishers:
            manager = self.publishers[websocket]
            await manager.cleanup()
            del self.publishers[websocket]
            logger.info(f"Publisher disconnected. Total publishers: {len(self.publishers)}")

    async def disconnect_consumer(self, websocket: WebSocket):
        """Disconnect consumer and cleanup resources"""
        if websocket in self.consumers:
            manager = self.consumers[websocket]
            await manager.cleanup()
            del self.consumers[websocket]
            logger.info(f"Consumer disconnected. Total consumers: {len(self.consumers)}")



@app.websocket("/ws/publish/{client_id}")
async def websocket_publisher_endpoint(
    websocket: WebSocket,
    client_id: str,
    topic: str = Query(default="default-topic")
):
    manager = ConnectionManager()
    try:
        await manager.connect_publisher(websocket, client_id, topic)
        kafka_manager = manager.publishers[websocket]
        
        while True:
            message = await websocket.receive_text()
            data = {
                "client_id": client_id,
                "topic": topic,
                "message": message,
                "timestamp": asyncio.get_running_loop().time()
            }
            await kafka_manager.publish_message(data)
            
    except WebSocketDisconnect:
        logger.info(f"Publisher {client_id} disconnected")
        await manager.disconnect_publisher(websocket)
    except Exception as e:
        logger.error(f"Error in publisher endpoint: {e}")
        await manager.disconnect_publisher(websocket)

@app.websocket("/ws/subscribe/{client_id}")
async def websocket_subscriber_endpoint(
    websocket: WebSocket,
    client_id: str,
    topic: str = Query(default="default-topic")
):
    manager = ConnectionManager()
    try:
        await manager.connect_subscriber(websocket, client_id, topic)
        
        # Keep the connection alive
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        logger.info(f"Subscriber {client_id} disconnected")
        await manager.disconnect_consumer(websocket)
    except Exception as e:
        logger.error(f"Error in subscriber endpoint: {e}")
        await manager.disconnect_consumer(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8101)
