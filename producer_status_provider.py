import asyncio
from os import environ
import sys
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner


class ProducerStatusProvider(ApplicationSession):
    """
    An application component calling the different backend procedures.
    """
    async def onConnect(self):
        self.join(self.config.realm, [u"ticket"], 'metadata_provider')

    async def onChallenge(self, challenge):
        if challenge.method == u"ticket":
            return environ.get('MANTATO_PROVIDER_TICKET')
        else:
            raise Exception("Invalid authmethod {}".format(challenge.method))

    async def onJoin(self, details):
        if len(sys.argv) < 2 or sys.argv[1] == '0':
            await self.call('com.metadata.switch_to_autopilot')
            print("Switched to autopilot")
        else:
            await self.call('com.metadata.switch_to_autopilot', sys.argv[1])
            print("Switched to producer", sys.argv[1])

        self.leave()

    def onDisconnect(self):
        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("MANTATO_AUTOBAHN_ROUTER", u"ws://127.0.0.1/ws"),
        u"metadata-realm",
    )

    runner.run(ProducerStatusProvider)