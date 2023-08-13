import os
import time
from dataclasses import dataclass

from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis


def safe_get(dictionary, key):
    # return the string representation, because sometimes the value is an object, rather than the required
    # string
    if key in dictionary:
        val = dictionary[key]
        return str(val) if not isinstance(val, list) else val
    else:
        return ''


def format_duration(track_length):
    duration_format = "%M:%S" if track_length < 3600 else "%H:%M:%S"
    return time.strftime(duration_format, time.gmtime(track_length))


def squeeze(list_or_str):
    if isinstance(list_or_str, list):
        return ", ".join(str(x) for x in list_or_str)
    elif isinstance(list_or_str, str):
        return list_or_str
    else:
        return ''


def format_url(release_id):
    return 'https://musicbrainz.org/release/{0}'.format(release_id) if len(release_id) > 0 else ''


@dataclass
class SlotMetadata:
    # The name of the producer or Autopilot (special name)
    # Source: Producer dashboard (i.e., JS client in a webpage, or Python client in a desktop app)
    producer_name: str = 'Autopilot'
    # The name of the slot/zone in case of autopilot or name of show
    # Source: Scheduler or Producer dashboard
    title: str = ''
    # The duration of the zone or the show in form of start-end, e.g. 10:00-12:00
    # Source: Scheduler or Producer dashboard
    duration: str = ''
    # Auxiliary message (in case of a show)
    # Source: Producer dashboard
    auxiliary_message: str = ''
    # Description of zone or show
    # Source: Scheduler or Producer dashboard
    description: str = ''
    # Zone or show URL (e.g. in website)
    # Source: Scheduler or Producer dashboard
    url = ''
    # Coverart URL of the album in case of autopilot or the cover of a show
    # Source: Scheduler or dashboard/db
    image_url = ''

    def update_from_scheduler_json(self, scheduler_message):
        current_song = scheduler_message['current_song']
        current_zone = current_song['Zone']
        if self.title == current_zone:
            return

        # Only the zone name is sent from the scheduler / rest info should be obtained from an API / not avail. now
        self.title = current_zone

    def to_partial_message(self):
        partial_message = \
            {
                'producerName': self.producer_name,
                'slotTitle': self.title,
                'slotDuration': self.duration,
                'slotAuxiliaryMessage': self.auxiliary_message,
                'slotDescription': self.description,
                'slotURL': self.url,
                'imageUrl': self.image_url
            }

        return partial_message


@dataclass
class AudioFileMetadata:
    filepath: str = ''
    album_title: str = ''
    song_title: str = ''
    song_length: str = ''
    artist: str = ''
    genre: str = ''
    date: str = ''
    metadata_url: str = ''

    def update_from_scheduler_json(self, scheduler_message):
        self.filepath = scheduler_message['current_song']['Path']
        file_extension = os.path.splitext(self.filepath)[-1]
        if not os.path.exists(self.filepath) or file_extension not in ['.mp3', '.flac', '.ogg']:
            return
        elif file_extension == '.mp3':
            self._parse_mp3()
        elif file_extension in ['.flac', '.ogg']:
            self._parse_vorbis()
        else:
            assert False

    def _parse_mp3(self):
        id3_metadata = ID3(self.filepath)
        self.album_title = safe_get(id3_metadata, 'TALB')
        self.song_title = safe_get(id3_metadata, 'TIT2')
        self.song_length = format_duration(MP3(self.filepath).info.length)
        self.artist = safe_get(id3_metadata, 'TPE1')
        self.genre = safe_get(id3_metadata, 'TCON')
        self.date = safe_get(id3_metadata, 'TDRL')
        self.metadata_url = format_url(safe_get(id3_metadata, 'TXXX:MusicBrainz Album Id'))

    def _parse_vorbis(self):
        file_extension = os.path.splitext(self.filepath)[-1]
        vorbis_metadata = FLAC(self.filepath) if file_extension == '.flac' else OggVorbis(self.filepath)
        self.album_title = squeeze(safe_get(vorbis_metadata, 'album'))
        self.song_title = squeeze(safe_get(vorbis_metadata, 'title'))
        self.song_length = format_duration(vorbis_metadata.info.length)
        self.artist = squeeze(safe_get(vorbis_metadata, 'artist'))
        self.genre = squeeze(safe_get(vorbis_metadata, 'genre'))
        self.date = squeeze(safe_get(vorbis_metadata, 'date'))
        self.metadata_url = format_url(squeeze(safe_get(vorbis_metadata, 'musicbrainz_albumid')))

    def to_partial_message(self):
        partial_message = \
            {
                'albumTitle': self.album_title,
                'songTitle': self.song_title,
                'songLength': self.song_length,
                'artist': self.artist,
                'genre': self.genre,
                'date': self.date,
                'metadata_url': self.metadata_url
            }

        return partial_message

