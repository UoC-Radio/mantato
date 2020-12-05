import asyncio
from os import environ
from autobahn.asyncio.wamp import ApplicationSession
from autobahn_autoreconnect import ApplicationRunner
from datetime import datetime

class DummyListener(ApplicationSession):
    """
    An application component that subscribes and receives events, and
    stop after having received 5 events.
    """

    async def onJoin(self, details):
        def on_event(message):
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print(f"[{current_time}] Got event: {message}")

        await self.subscribe(on_event, 'com.metadata.client.metadata_event')

    async def onConnect(self):
        self.join(self.config.realm, ['anonymous'])

    def onDisconnect(self):
        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    runner = ApplicationRunner(environ.get("MANTATO_AUTOBAHN_ROUTER", u"ws://127.0.0.1/ws"), u"metadata-realm")
    try:
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(runner.run(DummyListener), loop=loop)
        loop.run_forever()
    except Exception as e:
        print(e)