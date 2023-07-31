#!/usr/bin/env python3
import json
import re
import threading
from math import ceil
from os import environ
from sys import exit
from time import sleep, time

import requests
from pika import (BasicProperties, BlockingConnection, ConnectionParameters,
                  PlainCredentials)


class AudioSchedulerProxy(threading.Thread):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        broker_host = environ.get("MANTATO_BROKER_HOST", u"127.0.0.1")
        broker_port = environ.get("MANTATO_BROKER_PORT", u"5672")
        scheduler_host = environ.get('MANTATO_SCHEDULER_IP', "127.0.0.1")

        self._metadata_address = f'http://{scheduler_host}:9670'
        self._queue_name = 'scheduler_metadata_queue'
        self._exchange_name = 'scheduler_metadata_exchange'

        credentials = PlainCredentials("guest", "guest")
        parameters = ConnectionParameters(
            host=broker_host, port=broker_port, credentials=credentials)
        self._connection = BlockingConnection(parameters)
        self._topic = 'com.metadata.item_scheduled'

        self._channel = self._connection.channel()
        self._channel.queue_declare(queue=self._queue_name, auto_delete=True)
        self._channel.exchange_declare(
            exchange=self._exchange_name, exchange_type='topic')

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

    def stop(self):
        print("Stopping...")
        self._is_running = False
        # Wait until all the data events have been processed
        self._connection.process_data_events(time_limit=1)
        if self._connection.is_open:
            self._connection.close()
        print("Stopped")

    def _publish(self, message):
        self._channel.basic_publish(exchange=self._exchange_name,
                                    routing_key=self._topic,
                                    body=json.dumps(message),
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
    publisher = AudioSchedulerProxy()

    try:
        publisher.start()
    except KeyboardInterrupt:
        publisher.stop()
    finally:
        publisher.join()
