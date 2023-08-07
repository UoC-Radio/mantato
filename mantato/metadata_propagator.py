#!/usr/bin/env python3
from os import environ, path
import json
import time
from typing import Literal

import json
import re
import threading
from math import ceil
from os import environ
from sys import exit
from time import sleep, time
import os
import requests

from pika import (BasicProperties, BlockingConnection, ConnectionParameters,
                  PlainCredentials, exceptions)
from retry import retry

from mantato.metadata_utils import SlotMetadata, AudioFileMetadata
from mantato.messaging_utils import MessagingEntity, run


class MetadataRouter(MessagingEntity):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._initialize_connection()
        self._initialize_queues()

        self._is_running = True

        self._slot_metadata = SlotMetadata()
        self._audio_file_metadata = AudioFileMetadata()

        # Keep the message from the scheduler in order to use it when switching back from producer, to immediately
        # handle and send the current metadata
        self.last_scheduler_message = {}

        # Last JSON event
        self.last_event = None

    def run(self):
        def callback(ch, method, properties, body):
            self._handle_scheduler_message(json.loads(body))

        self._channel.basic_consume(
            queue=self._scheduler_queue_name, on_message_callback=callback, auto_ack=True)

        self._channel.start_consuming()

    def _initialize_queues(self):
        # Incoming queue settings
        self._scheduler_exchange_name = 'scheduler_metadata_exchange'
        self._scheduler_queue_name = 'scheduler_metadata_queue'
        self._scheduler_topic = 'com.metadata.item_scheduled'

        self._channel.exchange_declare(
            exchange=self._scheduler_exchange_name, exchange_type='topic')

        # Consider a message not consumed within 10 seconds as invalid
        queue_arguments = \
            {
                'x-message-ttl': 10000
            }

        self._channel.queue_declare(queue=self._scheduler_queue_name, auto_delete=True, arguments=queue_arguments)
        self._channel.queue_bind(exchange=self._scheduler_exchange_name, queue=self._scheduler_queue_name,
                                 routing_key=self._scheduler_topic)

        # Outgoing queue settings
        self._exchange_name = 'propagator_metadata_exchange'
        self._topic = 'com.metadata.metadata_event'

        self._channel.exchange_declare(exchange=self._exchange_name, exchange_type='topic')

    def _send_event(self, json_string):
        self.last_event = json_string

        print('Sending event', json_string)
        self._publish(json_string)

    def _publish(self, message):
        # TODO: Make it partial function since most parameters are same for all calls
        self._channel.basic_publish(exchange=self._exchange_name,
                                    routing_key=self._topic,
                                    body=json.dumps(message).encode(),
                                    properties=BasicProperties(
                                        content_type='application/json')
                                    )

    def _handle_scheduler_message(self, scheduler_message, force_send=False):
        print(f'Received scheduler message {scheduler_message}')
        if not scheduler_message:
            return

        self.last_scheduler_message = scheduler_message

        # Omit the scheduler message if a producer is live
        if self._slot_metadata.producer_name != 'Autopilot':
            return

        previous_filepath = self._audio_file_metadata.filepath

        self._slot_metadata.update_from_scheduler_json(scheduler_message)
        self._audio_file_metadata.update_from_scheduler_json(scheduler_message)

        # Publish event only if the file that is sent is different. Handles case when scheduler metadata provider is
        # restarted
        if previous_filepath != self._audio_file_metadata.filepath or force_send:
            # Create a message by merging slot/zone metadata with audio file metadata
            message = self._slot_metadata.to_partial_message() | self._audio_file_metadata.to_partial_message()
            self._send_event(message)

    def _update_zone(self, zone_name):
        self._slot_metadata.slot_title = zone_name

    # def switch_to_producer(self, producer_name):
    #     self.producer_name = producer_name
    #     json_string = self.create_metadata_string('')
    #     self.send_event(json_string)
    #     return 'Switched to producer:{0}.'.format(producer_name)
    #
    # def switch_to_autopilot(self):
    #     self.producer_name = 'Autopilot'
    #     self.handle_scheduler_message(self.last_scheduler_message, force_send=True)
    #     return 'Switched to Autopilot.'
    #
    # def item_scheduled(self, scheduler_message):
    #     self.handle_scheduler_message(scheduler_message)
    #
    # def get_latest_scheduled(self):
    #     return self.last_event


if __name__ == "__main__":
    run(MetadataRouter)
