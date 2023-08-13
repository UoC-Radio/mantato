import os
import threading
from abc import abstractmethod
from dataclasses import dataclass, field
from functools import partial

from pika import PlainCredentials, BlockingConnection, ConnectionParameters, exceptions
from retry import retry


@dataclass
class ConnectionOptions:
    broker_host: str = field(default_factory=partial(os.environ.get, 'MANTATO_BROKER_HOST', '127.0.0.1'))
    broker_port: int = field(default_factory=partial(os.environ.get, 'MANTATO_BROKER_PORT', 5672))
    broker_vhost: str = field(default_factory=partial(os.environ.get, 'MANTATO_BROKER_VHOST', '/'))
    username: str = field(default_factory=partial(os.environ.get, 'MANTATO_USERNAME', 'guest'))
    password: str = field(default_factory=partial(os.environ.get, 'MANTATO_PASSWORD', 'guest'))


class MessagingEntity(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._is_running = True

    def _initialize_connection(self):
        connection_options = ConnectionOptions()

        # Connection settings
        credentials = PlainCredentials(connection_options.username, connection_options.password)
        parameters = ConnectionParameters(
            host=connection_options.broker_host,
            port=connection_options.broker_port,
            virtual_host=connection_options.broker_vhost,
            credentials=credentials)

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

