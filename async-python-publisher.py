"""
Python WebSocket Publisher Client with Topic Selection
"""
import asyncio
import websockets
import json
import logging
from datetime import datetime
import random
import uuid
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PublisherClient:
    def __init__(self, websocket_url: str, topic: str):
        self.base_url = websocket_url
        self.topic = topic
        self.running = True
        self.client_id = str(uuid.uuid4())
        self.websocket = None

    @property
    def websocket_url(self):
        """Construct WebSocket URL with client ID and topic"""
        return f"{self.base_url}/ws/publish/{self.client_id}?topic={self.topic}"

    async def connect(self):
        """Establish WebSocket connection"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            logger.info(f"Publisher {self.client_id} connected to topic {self.topic}")
            return True
        except Exception as e:
            logger.error(f"Connection failed for publisher {self.client_id}: {e}")
            return False

    async def disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            logger.info(f"Publisher {self.client_id} disconnected from topic {self.topic}")

    async def publish_messages(self):
        """Publish messages to WebSocket"""
        if not self.websocket:
            logger.error("No active WebSocket connection")
            return

        try:
            while self.running:
                message = {
                    "client_id": self.client_id,
                    "id": random.randint(1, 1000),
                    "topic": self.topic,
                    "timestamp": datetime.utcnow().isoformat(),
                    "content": f"Test message for topic {self.topic}: {random.randint(1, 100)}"
                }
                
                await self.websocket.send(json.dumps(message))
                logger.info(f"Published to topic {self.topic}: {message}")
                
                await asyncio.sleep(2)
                
        except websockets.exceptions.ConnectionClosed:
            logger.error(f"WebSocket connection closed for publisher {self.client_id}")
        except Exception as e:
            logger.error(f"Error in publisher {self.client_id}: {e}")
        finally:
            await self.disconnect()

    def stop(self):
        """Stop the publisher"""
        self.running = False

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Kafka WebSocket Publisher')
    parser.add_argument('--topic', type=str, default='default-topic',
                      help='Kafka topic to publish to')
    parser.add_argument('--host', type=str, default='localhost',
                      help='WebSocket server host')
    parser.add_argument('--port', type=int, default=8000,
                      help='WebSocket server port')
    args = parser.parse_args()

    websocket_base_url = f"ws://{args.host}:{args.port}"
    publisher = PublisherClient(websocket_base_url, args.topic)
    
    try:
        if await publisher.connect():
            await publisher.publish_messages()
    except KeyboardInterrupt:
        logger.info("Publisher stopped by user")
        publisher.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await publisher.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
