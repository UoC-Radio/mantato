import time
from mutagen.id3 import PictureType
import mimetypes
from paramiko import SSHClient
from scp import SCPClient
from PIL import Image
import io
import os


def safe_get(dictionary, key):
    # return the string representation, because sometimes the value is an object, rather than the required string
    if key in dictionary:
        val = dictionary[key]
        return str(val) if not isinstance(val, list) else val
    else:
        return ''


def format_duration(track_length):
    duration_format = "%M:%S" if track_length < 3600 else "%H:%M:%S"
    return time.strftime(duration_format, time.gmtime(track_length))


def squeeze(l):
    if isinstance(l, list):
        return ", ".join(str(x) for x in l)
    elif isinstance(l, str):
        return l
    else:
        return ''


# TODO add support for discogs url
def format_url(release_id):
    return 'https://musicbrainz.org/release/{0}'.format(release_id) if len(release_id) > 0 else ''


def get_id3_front_cover(metadata):
    # From what I have seen is some examples, in case of multiple images 'APIC:' contains the front cover,
    # while 'APIC(1):', 'APIC(2):', etc contain the rest images
    if 'APIC:' in metadata and metadata['APIC:'].type == PictureType.COVER_FRONT:
        return metadata['APIC:'].data, metadata['APIC:'].mime
    else:
        return None, None


def get_vorbis_front_cover(metadata):
    if len(metadata.pictures) > 0 and metadata.pictures[0].type == PictureType.COVER_FRONT:
        return metadata.pictures[0].data, metadata.pictures[0].mime
    else:
        return None, None


def prepare_cover(data, img_path):
    # Read image from binary data (no matter the mime type, then save as jpg)
    img = Image.open(io.BytesIO(data))
    # Resize to a fixed size (hardcoded / don't keep aspect ratio)
    img = img.resize((256, 256), Image.ANTIALIAS)
    img.save(img_path)


def copy_to_remote(local_path, remote_path, host, port, username):
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(host, port, username)
    scp = SCPClient(ssh.get_transport())
    scp.put(local_path, remote_path)
    scp.close()
    ssh.close()


