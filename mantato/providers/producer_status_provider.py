#!/usr/bin/env python
import pika
import uuid
import json
import sys

class ProducerStatusProvider(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))

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

    def call(self, producer_name):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='switch_producer',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=producer_name)
        self.connection.process_data_events(time_limit=None)
        return self.response


producer_status_rpc = ProducerStatusProvider()

if len(sys.argv) < 2 or sys.argv[1] == '0':
    producer_name = 'Autopilot'
    response = producer_status_rpc.call('Autopilot')
    print("Switched to autopilot")
else:
    producer_name = sys.argv[1]
    response = producer_status_rpc.call(sys.argv[1])
    print("Switched to producer", sys.argv[1])
