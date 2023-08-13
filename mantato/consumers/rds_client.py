#!/usr/bin/env python3
import json
import subprocess
from shutil import which
from sys import exit

from mantato.consumers.consumer_base import ConsumerBase
from mantato.messaging_utils import run


class RDSUpdater(ConsumerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._rds_tool_executable_name = 'rds_tool'

        # Locate rds_tool
        if not which(self._rds_tool_executable_name):
            exit(f'{self._rds_tool_executable_name} executable not found in the system.')

        self._update_rt = True

    def callback(self, ch, method, properties, body):
        if not self._update_rt:
            return

        data = json.loads(body)

        # Simple strategy, cut from the end
        rds_message = '\"{} by {}\"'.format(data['songTitle'], data['artist'])[:64]

        print('Message for RDS: {}'.format(rds_message))

        cmd = ['rds_tool', '-rt', rds_message]
        subprocess.run(cmd)


if __name__ == "__main__":
    run(RDSUpdater)
