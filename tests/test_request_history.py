#!/usr/bin/env python
import json
import uuid

import pika
from dotenv import load_dotenv
from pika import PlainCredentials, ConnectionParameters, BlockingConnection

from mantato.messaging_utils import ConnectionOptions


class MessageHistoryRpcClient(object):

    def __init__(self):
        load_dotenv('../etc/.env')

        connection_options = ConnectionOptions(username='rastapank-listener', password='guest')

        # Connection settings
        credentials = PlainCredentials(connection_options.username, connection_options.password)
        parameters = ConnectionParameters(
            host=connection_options.broker_host,
            port=connection_options.broker_port,
            virtual_host=connection_options.broker_vhost,
            credentials=credentials)

        self.connection = BlockingConnection(parameters)

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='propagator_history_exchange',
            routing_key='message_history',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body='')
        self.connection.process_data_events(time_limit=None)
        return self.response


msg_history_rpc = MessageHistoryRpcClient()

print(" [x] Requesting message history")
response = msg_history_rpc.call()
print(f" [.] Got {json.loads(response)}")
