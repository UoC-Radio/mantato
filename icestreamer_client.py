#!/usr/bin/env python3
from sys import exit
from os import environ
import asyncio
import autobahn.wamp.exception
from autobahn.twisted.wamp import ApplicationSession
from autobahn.twisted.wamp import ApplicationRunner
# from autobahn_autoreconnect import ApplicationRunner
from shutil import which
import subprocess
import json
from enum import Enum


class IcestreamerUpdater(ApplicationSession):
    def __init__(self, *args, **kwargs):
        super(IcestreamerUpdater, self).__init__(*args, **kwargs)
        self._filepath = environ.get('MANTATO_ICESTREAMER_METADATA_FILE', '/tmp/icestreamer_metadata')

    async def onConnect(self):
        self.join(self.config.realm, [u"ticket"], 'metadata_service')

    async def onChallenge(self, challenge):
        if challenge.method == u"ticket":
            return environ.get('MANTATO_SERVICE_TICKET')
        else:
            raise Exception("Invalid authmethod {}".format(challenge.method))

    async def onJoin(self, details):
        # listening for the corresponding message from the "backend"
        # (any session that .publish()es to this topic).

        def write_info(msg):
            data = json.loads(msg)

            with open(self._filepath, 'w') as f:
                f.writelines([data['artist'] + '\n', data['songTitle'] + '\n'])

        reg = await self.register(write_info, u'com.metadata.icestreamer.write_info')
        print("registered 'com.metadata.icestreamer.write_info' with id {0}".format(reg.id))


if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("MANTATO_AUTOBAHN_ROUTER", u"ws://127.0.0.1/ws"),
        u"metadata-realm",
    )
    runner.run(IcestreamerUpdater, auto_reconnect=True)
