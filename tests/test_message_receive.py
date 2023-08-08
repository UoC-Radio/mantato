#!/usr/bin/env python3
import json
from os import environ
from mantato.messaging_utils import run
from mantato.consumers.consumer_base import ConsumerBase


class DummyMessageReceiver(ConsumerBase):
    def callback(self, ch, method, properties, body):
        data = json.loads(body)
        print(data)


if __name__ == "__main__":
    run(DummyMessageReceiver)


