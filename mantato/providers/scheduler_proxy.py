#!/usr/bin/env python3
import json
from math import ceil
from os import environ
from time import sleep, time

import requests
from pika import (BasicProperties)

from mantato.messaging_utils import MessagingEntity, run


class AudioSchedulerProxy(MessagingEntity):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._initialize_connection()
        self._initialize_queues()

        scheduler_host = environ.get('MANTATO_SCHEDULER_IP', "127.0.0.1")
        self._metadata_address = f'http://{scheduler_host}:9670'

        self._next_check = int(time())
        self._is_running = True

    def run(self):
        while self._is_running:
            self._connection.process_data_events(time_limit=1)

            if int(time()) > self._next_check:
                data = self._get_metadata()

                if data is not None:
                    print(data)
                    self._connection.add_callback_threadsafe(
                        lambda: self._publish(data))

            sleep(1)

    def _initialize_queues(self):
        # Outgoing queue settings
        self._exchange_name = 'scheduler_metadata_exchange'
        self._topic = 'com.metadata.item_scheduled'

        self._channel.exchange_declare(
            exchange=self._exchange_name, exchange_type='topic')

    def _publish(self, message):
        self._channel.basic_publish(exchange=self._exchange_name,
                                    routing_key=self._topic,
                                    body=json.dumps(message).encode(),
                                    properties=BasicProperties(
                                        content_type='application/json')
                                    )

    def _get_metadata(self):
        try:
            r = requests.get(self._metadata_address)
        except requests.exceptions.RequestException as e:
            # e.errno, e.strerror
            return None

        try:
            data = json.loads(r.text)
        except json.decoder.JSONDecodeError:
            print(r.text)
            raise Exception("Strange JSON {}".format(r.text))

        duration = int(data['current_song']['Duration'])
        elapsed = int(data['current_song']['Elapsed'])
        overlap = int(data['overlap'])

        next = duration - elapsed - ceil(overlap / 2)
        
        self._next_check = int(time()) + next

        return data


if __name__ == "__main__":
    run(AudioSchedulerProxy)
