#!/usr/bin/env python3
import json

from dotenv import load_dotenv
from pika import PlainCredentials, ConnectionParameters, BlockingConnection

from mantato.consumers.consumer_base import ConsumerBase
from mantato.messaging_utils import run, ConnectionOptions


class DummyMessageReceiver(ConsumerBase):
    def _initialize_connection(self):
        load_dotenv('../etc/.env')

        # Override the default options in order to manually connect with a guest user
        connection_options = ConnectionOptions(username='rastapank-listener', password='guest')

        # Connection settings
        credentials = PlainCredentials(connection_options.username, connection_options.password)
        parameters = ConnectionParameters(
            host=connection_options.broker_host,
            port=connection_options.broker_port,
            virtual_host=connection_options.broker_vhost,
            credentials=credentials)

        self._connection = BlockingConnection(parameters)
        self._channel = self._connection.channel()

    def callback(self, ch, method, properties, body):
        data = json.loads(body)
        print(data)


if __name__ == "__main__":
    run(DummyMessageReceiver)


