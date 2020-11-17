#!/usr/bin/env python3
import sys
sys.path.append("/tmp/TEST")

from os import environ, path
import json
import asyncio
from mutagen.oggvorbis import OggVorbis
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.flac import FLAC

import metadata_utils as mu
from autobahn.asyncio.wamp import ApplicationSession
#from autobahn.asyncio.wamp import ApplicationRunner
from autobahn_autoreconnect import ApplicationRunner


class MetadataPropagator(ApplicationSession):

    def __init__(self, *args, **kwargs):
        super(MetadataPropagator, self).__init__(*args, **kwargs)
        # Source: Producer dashboard (i.e., JS client in a webpage, or Python client in a desktop app)
        # Functionality "Go live / Go offline"
        self.producer_name = 'Autopilot'
        # Source: Scheduler or Producer dashboard
        # TODO: Ignore scheduler updates when the producer is not the Autopilot
        self.slot_title = 'Slot Title'
        # Source: Scheduler or Producer dashboard
        # TODO: Same as above
        self.slot_duration = 'Slot Duration'
        # Source: Producer dashboard
        self.slot_auxiliary_message = 'A message about the playlist'
        # Source: Scheduler or Producer dashboard
        # TODO: Same as above
        self.slot_description = 'A pretty long description about the playlist.'
        # Source: Scheduler or Producer dashboard
        # TODO: Same as above
        self.slot_URL = 'http://www.radio.uoc.gr/playlist_name.html'
        # Source: Scheduler (image of a show) OR metadata
        # An option to send either the image of the album, image for the playlist or the image for the show.
        self.image_from_album = True
        self.image_URL = 'http://afrijamz.com/wp-content/uploads/beetles.jpg'
        # Rest options are read from audio file metadata

        # Keep the message from the scheduler in order to use it when switching back from producer, to immediately
        # handle and send the current metadata
        self.last_scheduler_message = {}

        self.zones = []
        self.schedule = []

        # Last JSON event
        self.last_event = ""

        # Last file
        self.last_file = ""

    def load_zones(self):
        pass

    def load_schedule(self):
        pass

    def update_zone(self, zone_name):
        self.slot_title = zone_name

    def fill_empty_audio_metadata(self, message):
        message['albumTitle'] = ''
        message['songTitle'] = ''
        message['songLength'] = ''
        message['artist'] = ''
        message['genre'] = ''
        message['year'] = ''
        message['metadata_url'] = ''
        if self.image_from_album:
            message['imageUrl'] = ''

    def parse_metadata_from_file(self, filepath, message):
        test_parsing_succeded = True

        # Step 1. Read file and read an auxiliary metadata field

        # Step 2. In case of success continue to fill the message
        if test_parsing_succeded:
            file_extension = filepath.split('.')[-1]
            if file_extension == 'mp3':
                id3_metadata = ID3(filepath)
                message['albumTitle'] = mu.safe_get(id3_metadata, 'TALB')
                message['songTitle'] = mu.safe_get(id3_metadata, 'TIT2')
                message['songLength'] = mu.format_duration(MP3(filepath).info.length)
                message['artist'] = mu.safe_get(id3_metadata, 'TPE1')
                message['genre'] = mu.safe_get(id3_metadata, 'TCON')
                message['year'] = mu.safe_get(id3_metadata, 'TDRL')
                message['metadata_url'] = mu.format_url(mu.safe_get(id3_metadata, 'TXXX:MusicBrainz Album Id'))

                data, _ = mu.get_id3_front_cover(id3_metadata)

            elif file_extension == 'flac' or file_extension == 'ogg':
                vorbis_metadata = FLAC(filepath) if file_extension == 'flac' else OggVorbis(filepath)
                message['albumTitle'] = mu.squeeze(mu.safe_get(vorbis_metadata, 'album'))
                message['songTitle'] = mu.squeeze(mu.safe_get(vorbis_metadata, 'title'))
                message['songLength'] = mu.format_duration(vorbis_metadata.info.length)
                message['artist'] = mu.squeeze(mu.safe_get(vorbis_metadata, 'artist'))
                message['genre'] = mu.squeeze(mu.safe_get(vorbis_metadata, 'genre'))
                message['year'] = mu.squeeze(mu.safe_get(vorbis_metadata, 'date'))
                message['metadata_url'] = mu.format_url(mu.squeeze(mu.safe_get(vorbis_metadata, 'musicbrainz_albumid')))

                data, _ = mu.get_vorbis_front_cover(vorbis_metadata)
            else:
                self.fill_empty_audio_metadata(message)
                data = None

            if self.image_from_album:
                if data is not None:
                    local_path = '/tmp/cover.jpg'
                    mu.prepare_cover(data, local_path)
                else:
                    local_path = './fallback_cover.jpg'

                remote_path = '/dev/shm/cover.jpg'    
                              
                mu.copy_to_remote(local_path, remote_path, 'eden.radio.uoc.gr', 22, 'metadata')
                
                # Redundant for now
                message['imageUrl'] = 'http://radio.uoc.gr/metadata/cover.jpg'
        else:
            self.fill_empty_audio_metadata(message)

    def create_metadata_string(self, filepath):
        # Open template
        message = ''
        with open('message.json') as json_data:
            message = json.load(json_data)
            message['producerName'] = self.producer_name
            message['slotTitle'] = self.slot_title
            message['slotDuration'] = self.slot_duration
            message['slotAuxiliaryMessage'] = self.slot_auxiliary_message
            message['slotDescription'] = self.slot_description
            message['slotURL'] = self.slot_URL
            message['imageUrl'] = self.image_URL

            # Fill the rest by parsing the file
            try:            
                self.parse_metadata_from_file(filepath, message)
            except Exception as err: # Generic exception for catching exceptions with problematic files (maybe need to narrow the exception for logging)
                print(err)
                self.fill_empty_audio_metadata(message)

        # JSON requires double quotes for strings
        return json.dumps(message, ensure_ascii=False)

    def handle_scheduler_message(self, scheduler_message):

        if not self.last_scheduler_message:
            return

        self.last_scheduler_message = scheduler_message

        # Omit the scheduler message if a producer is live
        if self.producer_name != 'Autopilot':
            return

        # Check if the zone has changed
        current_zone = scheduler_message['current_song']['Zone']
        if self.slot_title != current_zone:
            self.update_zone(current_zone)

        filepath = scheduler_message['current_song']['Path']

        # Publish event only if the file that is sent is different.
        # Bypasses some spurious cases when metadata provider sends multiple times the same file
        if filepath != self.last_file:
            json_string = self.create_metadata_string(filepath)
            self.send_event(json_string)

        self.last_file = filepath

    def handle_dashboard_message(self, dashboard_message):
        pass

    def send_event(self, json_string):
        self.last_event = json_string
        self.publish(u'com.metadata.client.metadata_event', json_string)
        self.call(u'com.metadata.rds.send_rds', json_string)
        self.call(u'com.metadata.icestreamer.write_info', json_string)

    async def onConnect(self):
        self.join(self.config.realm, [u"ticket"], 'metadata_propagator')

    async def onChallenge(self, challenge):
        if challenge.method == u"ticket":
            return environ.get('MANTATO_PROPAGATOR_TICKET')
        else:
            raise Exception("Invalid authmethod {}".format(challenge.method))

    async def onJoin(self, details):
        def switch_to_producer(producer_name):
            self.producer_name = producer_name
            json_string = self.create_metadata_string('')
            self.send_event(json_string)
            return 'Switched to producer:{0}.'.format(producer_name)

        def switch_to_autopilot():
            self.producer_name = 'Autopilot'
            self.handle_scheduler_message(self.last_scheduler_message)
            return 'Switched to Autopilot.'

        def item_scheduled(scheduler_message):
            self.handle_scheduler_message(scheduler_message)

        def get_latest_scheduled():
            return self.last_event

        reg = await self.register(switch_to_producer, u'com.metadata.switch_to_producer')
        print("registered 'com.metadata.switch_to_producer' with id {0}".format(reg.id))
        reg = await self.register(switch_to_autopilot, u'com.metadata.switch_to_autopilot')
        print("registered 'com.metadata.switch_to_autopilot' with id {0}".format(reg.id))
        reg = await self.register(item_scheduled, u'com.metadata.item_scheduled')
        print("registered 'com.metadata.item_scheduled' with id {0}".format(reg.id))
        reg = await self.register(get_latest_scheduled, u'com.metadata.client.get_latest_scheduled')
        print("registered 'com.metadata.client.get_latest_scheduled' with id {0}".format(reg.id))


if __name__ == '__main__':
    runner = ApplicationRunner(environ.get("MANTATO_AUTOBAHN_ROUTER", u"ws://127.0.0.1/ws"), u"metadata-realm")

    try:
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(runner.run(MetadataPropagator), loop=loop)
        loop.run_forever()
    except Exception as e:
        print(e)
