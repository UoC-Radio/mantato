import time
from mutagen.id3 import PictureType
import mimetypes
from paramiko import SSHClient
from scp import SCPClient
from PIL import Image
import io
import os


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


