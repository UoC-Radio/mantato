#!/usr/bin/env python3
from sys import exit
from os import environ
import asyncio
import autobahn.wamp.exception
from autobahn.asyncio.wamp import ApplicationSession
# from autobahn.asyncio.wamp import ApplicationRunner
from autobahn_autoreconnect import ApplicationRunner
import requests
from math import ceil
import re
import json


class SchedulerMetadataProvider(ApplicationSession):
    def __init__(self, *args, **kwargs):
        super(SchedulerMetadataProvider, self).__init__(*args, **kwargs)
        ip = environ.get('MANTATO_SCHEDULER_IP', "127.0.0.1")
        self.__metadata_address = 'http://{}:9670'.format(ip)

    def get_metadata(self):
        try:
            r = requests.get(self.__metadata_address)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            # Awkward way to get the errno from the error message, because it is not stored in the object, unlike older
            # version of the library as reported in:
            # https://stackoverflow.com/questions/19370436/get-errno-from-python-requests-connectionerror
            # msg = e.args[0].reason.args[0]
            # errno = int(re.search(r"\[Errno\ ([0-9]+)\]", msg).group(1))
            # exit(errno)
            return None, 5

        try:
            data = json.loads(r.text)
        except json.decoder.JSONDecodeError:
            print(r.text)
            raise Exception("Strange JSON {}".format(r.text))

        duration = int(data['current_song']['Duration'])
        elapsed = int(data['current_song']['Elapsed'])
        overlap = int(data['overlap'])

        next = max(1, duration - elapsed - ceil(overlap / 2))

        return data, next

    async def onConnect(self):
        self.join(self.config.realm, [u"ticket"], 'metadata_provider')

    async def onChallenge(self, challenge):
        if challenge.method == u"ticket":
            return environ.get('MANTATO_PROVIDER_TICKET')
        else:
            raise Exception("Invalid authmethod {}".format(challenge.method))

    async def onJoin(self, details):
        while True:
            try:
                data, next = self.get_metadata()
                # quick fix for not calling multiple times during track change
                #if next < 1:
                #    continue
                if data is not None:
                    print(data)
                    _ = await self.call(u'com.metadata.item_scheduled', data)
                await asyncio.sleep(next)
            except autobahn.wamp.exception.TransportLost as e:
                exit(111)  # Connection refused error code
            except autobahn.wamp.exception.ApplicationError as e:
                exit(418)


if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("MANTATO_AUTOBAHN_ROUTER", u"ws://127.0.0.1/ws"),
        u"metadata-realm",
    )

    try:
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(runner.run(SchedulerMetadataProvider), loop=loop)
        loop.run_forever()
    except Exception as e:
        print(e)
