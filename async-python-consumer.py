"""
Python WebSocket Consumer Client with Topic Selection
"""
import asyncio
import websockets
import json
import logging
import uuid
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConsumerClient:
    def __init__(self, websocket_url: str, topic: str):
        self.base_url = websocket_url
        self.topic = topic
        self.running = True
        self.client_id = str(uuid.uuid4())
        self.websocket = None

    @property
    def websocket_url(self):
        """Construct WebSocket URL with client ID and topic"""
        return f"{self.base_url}/ws/subscribe/{self.client_id}?topic={self.topic}"

    async def connect(self):
        """Establish WebSocket connection"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            logger.info(f"Consumer {self.client_id} connected to topic {self.topic}")
            return True
        except Exception as e:
            logger.error(f"Connection failed for consumer {self.client_id}: {e}")
            return False

    async def disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            logger.info(f"Consumer {self.client_id} disconnected from topic {self.topic}")

    async def process_messages(self):
        """Process messages from WebSocket"""
        if not self.websocket:
            logger.error("No active WebSocket connection")
            return

        try:
            while self.running:
                message = await self.websocket.recv()
                try:
                    data = json.loads(message)
                    logger.info(f"Consumer {self.client_id} received from topic {self.topic}: {data}")
                    
                    # Send heartbeat to keep connection alive
                    await self.websocket.send(json.dumps({
                        "type": "heartbeat",
                        "client_id": self.client_id,
                        "topic": self.topic
                    }))
                    
                except json.JSONDecodeError:
                    logger.error(f"Consumer {self.client_id} received invalid JSON")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.error(f"WebSocket connection closed for consumer {self.client_id}")
        except Exception as e:
            logger.error(f"Error in consumer {self.client_id}: {e}")
        finally:
            await self.disconnect()

    def stop(self):
        """Stop the consumer"""
        self.running = False

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Kafka WebSocket Consumer')
    parser.add_argument('--topic', type=str, default='default-topic',
                      help='Kafka topic to subscribe to')
    parser.add_argument('--host', type=str, default='localhost',
                      help='WebSocket server host')
    parser.add_argument('--port', type=int, default=8000,
                      help='WebSocket server port')
    args = parser.parse_args()

    websocket_base_url = f"ws://{args.host}:{args.port}"
    consumer = ConsumerClient(websocket_base_url, args.topic)
    
    try:
        if await consumer.connect():
            await consumer.process_messages()
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
        consumer.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())