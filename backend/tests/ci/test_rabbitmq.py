import json
import logging
import os
import sys
import threading
import time
import uuid
from contextlib import contextmanager

import pytest

# Add the backend directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock implementation if needed for CI testing
try:
    import pika

    has_pika = True
except ImportError:
    has_pika = False
    logger.warning("pika not installed, using mock implementation for tests")

    class MockPikaConnection:
        def __init__(self, *args, **kwargs):
            self.is_closed = False

        def close(self):
            self.is_closed = True

    class MockPikaChannel:
        def __init__(self, *args, **kwargs):
            self.messages = {}
            self.callbacks = {}
            self.confirms = set()

        def queue_declare(self, queue, **kwargs):
            if queue not in self.messages:
                self.messages[queue] = []
            return type(
                "QueueDeclareResult",
                (),
                {"method": type("Method", (), {"queue": queue})},
            )

        def basic_publish(self, exchange, routing_key, body, **kwargs):
            if routing_key not in self.messages:
                self.messages[routing_key] = []
            self.messages[routing_key].append(body)

        def basic_consume(self, queue, on_message_callback, **kwargs):
            self.callbacks[queue] = on_message_callback
            return str(uuid.uuid4())

        def basic_ack(self, delivery_tag):
            self.confirms.add(delivery_tag)

        def start_consuming(self):
            time.sleep(0.1)  # Simulate brief consumption

        def stop_consuming(self):
            pass

    class MockPikaBlockingConnection:
        def __init__(self, *args, **kwargs):
            self.connection = MockPikaConnection()

        def __enter__(self):
            return self

        def __exit__(self, *args, **kwargs):
            self.connection.close()

        def channel(self):
            return MockPikaChannel()

        def close(self):
            self.connection.close()

    class MockPikaConnectionParameters:
        def __init__(self, host, **kwargs):
            self.host = host
            self.__dict__.update(kwargs)

    # Create mock pika module
    class MockPika:
        ConnectionParameters = MockPikaConnectionParameters
        BlockingConnection = MockPikaBlockingConnection

    pika = MockPika()


class RabbitMQLoadTest:
    """Test RabbitMQ performance under high load"""

    def __init__(self, url=None):
        """Initialize with RabbitMQ connection URL"""
        self.url = url or os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.connection = None
        self.channel = None
        self.test_queue = f"test_queue_{uuid.uuid4().hex[:8]}"
        self.message_count = 0
        self.processed_count = 0
        self.start_time = None
        self.end_time = None
        self.consumer_thread = None
        self.lock = threading.Lock()

    @contextmanager
    def rabbitmq_connection(self):
        """Create and manage a RabbitMQ connection"""
        try:
            # Parse the connection URL
            if self.url.startswith("amqp://"):
                parts = self.url.replace("amqp://", "").split(":")
                user_pass = parts[0].split("@")[0]
                host = parts[0].split("@")[1]
                port = int(parts[1].split("/")[0])
                vhost = parts[1].split("/")[1] if len(parts[1].split("/")) > 1 else "/"

                if ":" in user_pass:
                    username, password = user_pass.split(":")
                else:
                    username, password = user_pass, None
            else:
                # Default values
                username, password = "guest", "guest"
                host, port = "localhost", 5672
                vhost = "/"

            # Connect to RabbitMQ
            parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=vhost,
                credentials=(pika.PlainCredentials(username, password) if password else None),
                heartbeat=600,
                blocked_connection_timeout=300,
            )

            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            # Declare the queue
            result = channel.queue_declare(queue=self.test_queue, durable=True)
            self.test_queue = result.method.queue

            # Store the channel and connection
            self.channel = channel
            self.connection = connection

            yield

        finally:
            # Close connection
            if self.connection and not getattr(self.connection, "is_closed", True):
                self.connection.close()

    def callback(self, ch, method, properties, body):
        """Process received messages"""
        # Simulate processing time
        time.sleep(0.01)

        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)

        # Update count
        with self.lock:
            self.processed_count += 1

            # Log progress
            if self.processed_count % 100 == 0:
                elapsed = time.time() - self.start_time
                rate = self.processed_count / elapsed if elapsed > 0 else 0
                logger.info(
                    f"Processed {self.processed_count}/{self.message_count} messages "
                    f"({rate:.2f} msg/sec)"
                )

            # Check if we're done
            if self.processed_count >= self.message_count:
                self.end_time = time.time()

    def consumer_loop(self):
        """Run the message consumer"""
        with self.rabbitmq_connection():
            # Set QoS to avoid overwhelming the consumer
            self.channel.basic_qos(prefetch_count=10)

            # Setup consumer
            self.channel.basic_consume(queue=self.test_queue, on_message_callback=self.callback)

            # Start consuming
            logger.info("Starting consumer...")
            self.channel.start_consuming()

    def publish_messages(self, count):
        """Publish test messages to the queue"""
        with self.rabbitmq_connection():
            self.message_count = count
            self.processed_count = 0

            # Start timing
            self.start_time = time.time()

            # Publish messages
            logger.info(f"Publishing {count} messages...")
            for i in range(count):
                message = {
                    "id": i,
                    "timestamp": time.time(),
                    "data": f"Test message {i}",
                }

                self.channel.basic_publish(
                    exchange="",
                    routing_key=self.test_queue,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Make message persistent
                    ),
                )

                if (i + 1) % 100 == 0:
                    logger.info(f"Published {i + 1}/{count} messages")

            publish_time = time.time() - self.start_time
            publish_rate = count / publish_time if publish_time > 0 else 0
            logger.info(
                f"Published {count} messages in {publish_time:.2f}s ({publish_rate:.2f} msg/sec)"
            )

    def run_load_test(self, message_count=1000, max_time=60):
        """Run a complete load test"""
        # Start the consumer in a separate thread
        self.consumer_thread = threading.Thread(target=self.consumer_loop)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()

        # Wait for consumer to initialize
        time.sleep(1)

        # Publish messages
        self.publish_messages(message_count)

        # Wait for all messages to be processed or timeout
        timeout = time.time() + max_time
        while self.processed_count < self.message_count and time.time() < timeout:
            time.sleep(0.1)

        # Calculate results
        if self.end_time:
            elapsed_time = self.end_time - self.start_time
        else:
            elapsed_time = time.time() - self.start_time

        throughput = self.processed_count / elapsed_time if elapsed_time > 0 else 0

        # Log results
        logger.info(f"Test completed in {elapsed_time:.2f}s")
        logger.info(f"Published {self.message_count} messages")
        logger.info(f"Processed {self.processed_count} messages")
        logger.info(f"Throughput: {throughput:.2f} messages/second")

        # Return results
        return {
            "published": self.message_count,
            "processed": self.processed_count,
            "elapsed_time": elapsed_time,
            "throughput": throughput,
        }


@pytest.mark.skipif(not has_pika, reason="RabbitMQ pika library not available")
def test_rabbitmq_load_small():
    """Test RabbitMQ with a small burst of messages (100)"""
    load_test = RabbitMQLoadTest()
    results = load_test.run_load_test(message_count=100, max_time=30)

    # Assertions
    assert (
        results["processed"] == 100
    ), f"Not all messages were processed: {results['processed']}/100"
    assert results["throughput"] > 10, f"Throughput too low: {results['throughput']} msgs/sec"


@pytest.mark.skipif(not has_pika, reason="RabbitMQ pika library not available")
def test_rabbitmq_load_burst():
    """Test RabbitMQ with a large burst of messages (1000)"""
    load_test = RabbitMQLoadTest()
    results = load_test.run_load_test(message_count=1000, max_time=60)

    # Assertions
    assert (
        results["processed"] == 1000
    ), f"Not all messages were processed: {results['processed']}/1000"
    assert results["throughput"] > 50, f"Throughput too low: {results['throughput']} msgs/sec"


if __name__ == "__main__":
    if has_pika:
        print("Running RabbitMQ load tests...")
        test_rabbitmq_load_small()
        test_rabbitmq_load_burst()
    else:
        print("Skipping RabbitMQ tests - pika library not installed")
