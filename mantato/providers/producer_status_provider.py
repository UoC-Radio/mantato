#!/usr/bin/env python
import sys
import uuid

import pika
from pika import BlockingConnection, ConnectionParameters, PlainCredentials

from mantato.messaging_utils import ConnectionOptions


class ProducerStatusProvider(object):
    def __init__(self):
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

        result = self._channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self._channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

        self._response = None
        self._corr_id = None

    def on_response(self, ch, method, props, body):
        if self._corr_id == props.correlation_id:
            self._response = body

    def call(self, producer_name):
        self._response = None
        self._corr_id = str(uuid.uuid4())
        self._channel.basic_publish(
            exchange='',
            routing_key='switch_producer',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self._corr_id,
            ),
            body=producer_name)
        self._connection.process_data_events(time_limit=None)
        return self._response


def main():
    producer_status_rpc = ProducerStatusProvider()

    if len(sys.argv) < 2 or sys.argv[1] == '0':
        producer_name = 'Autopilot'
        response = producer_status_rpc.call('Autopilot')
        print("Switched to autopilot")
    else:
        producer_name = sys.argv[1]
        response = producer_status_rpc.call(sys.argv[1])
        print("Switched to producer", sys.argv[1])


if __name__ == "__main__":
    main()
