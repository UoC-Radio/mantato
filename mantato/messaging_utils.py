from os import environ
from abc import abstractmethod
import threading
from pika import PlainCredentials, BlockingConnection, ConnectionParameters, exceptions
from retry import retry


class MessagingEntity(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._is_running = True

    def _initialize_connection(self):
        broker_host = environ.get("MANTATO_BROKER_HOST", u"127.0.0.1")
        broker_port = environ.get("MANTATO_BROKER_PORT", u"5672")

        # Connection settings
        credentials = PlainCredentials("guest", "guest")
        parameters = ConnectionParameters(
            host=broker_host, port=broker_port, credentials=credentials)

        self._connection = BlockingConnection(parameters)
        self._channel = self._connection.channel()

    def _cleanup_connection(self):
        # Wait until all the data events have been processed
        self._connection.process_data_events(time_limit=1)
        if self._connection.is_open:
            self._connection.close()

    @abstractmethod
    def _initialize_queues(self):
        pass

    @abstractmethod
    def run(self):
        pass

    def stop(self):
        print("Stopping...")
        self._is_running = False
        self._cleanup_connection()
        print("Stopped")


@retry(exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def run(class_name):
    message_entity = class_name()

    try:
        message_entity.start()
    except KeyboardInterrupt:
        message_entity.stop()
    finally:
        message_entity.join()

