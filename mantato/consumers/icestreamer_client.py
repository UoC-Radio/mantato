#!/usr/bin/env python3
import json
from os import environ

from mantato.consumers.consumer_base import ConsumerBase
from mantato.messaging_utils import run


class IcestreamerUpdater(ConsumerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._filepath = environ.get('MANTATO_ICESTREAMER_METADATA_FILE', '/tmp/icestreamer_metadata')

    def callback(self, ch, method, properties, body):
        data = json.loads(body)

        with open(self._filepath, 'w') as f:
            f.writelines([data['artist'] + '\n', data['songTitle'] + '\n'])


def main():
    run(IcestreamerUpdater)


if __name__ == "__main__":
    main()

