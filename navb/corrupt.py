"""Fabrique des fichiers NAVB abîmés pour test"""
from pathlib import Path

from navb.format import HEADER, RECORD


def flip_byte(src, dst, record_index, byte_in_record=10):
    """Inverse 1 octet d'un enregistrement -> checksum ne correspond plus."""
    data = bytearray(Path(src).read_bytes())
    offset = HEADER.size + record_index * RECORD.size + byte_in_record
    data[offset] ^= 0xFF                     # ^ = XOR : inverse tous les bits
    Path(dst).write_bytes(data)


def truncate(src, dst, remove_bytes=10):
    """Coupe la fin du fichier -> simule enregistrement interrompu."""
    data = Path(src).read_bytes()
    Path(dst).write_bytes(data[:-remove_bytes])


def bad_magic(src, dst):
    """Remplace le magic -> plus un fichier NAVB valide."""
    data = bytearray(Path(src).read_bytes())
    data[0:4] = b"XXXX"
    Path(dst).write_bytes(data)