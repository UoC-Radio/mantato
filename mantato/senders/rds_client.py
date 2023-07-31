#!/usr/bin/env python3
from sys import exit
from os import environ
import asyncio
import autobahn.wamp.exception
from autobahn.asyncio.wamp import ApplicationSession
# from autobahn.asyncio.wamp import ApplicationRunner
from autobahn_autoreconnect import ApplicationRunner
from shutil import which
import subprocess
import json
from enum import Enum


class RDSUpdater(ApplicationSession):
    def __init__(self, *args, **kwargs):
        super(RDSUpdater, self).__init__(*args, **kwargs)
        self.__update_rt = True

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
        def send_rds(msg):
            if not self.__update_rt:
                return

            data = json.loads(msg)
            # Simple strategy, cut from the end
            rds_message = '\"{} by {}\"'.format(data['songTitle'], data['artist'])[:64]

            print('Message for RDS: {}'.format(rds_message))

            cmd = ['rds_tool', '-rt', rds_message]
            subprocess.run(cmd)

        def set_update_rt(status):
            pass

        # Locate rds_tool
        if not which('ls'):
           exit('rds_tool executable not found in the system. Please install it.')

        reg = await self.register(send_rds, u'com.metadata.rds.send_rds')
        print("registered 'com.metadata.rds.send_rds' with id {0}".format(reg.id))
        reg = await self.register(set_update_rt, u'com.metadata.rds.set_update_rt')
        print("registered 'com.metadata.rds.set_update_rt' with id {0}".format(reg.id))


if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("MANTATO_AUTOBAHN_ROUTER", u"ws://127.0.0.1/ws"),
        u"metadata-realm",
    )

    try:
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(runner.run(RDSUpdater), loop=loop)
        loop.run_forever()
    except Exception as e:
        print(e)
