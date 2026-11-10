"""Spécification du format NAVB."""
import struct

MAGIC = b"NAVB"          # b"..." = des octets, pas du texte
VERSION = 1

# "<" = little-endian, puis un code par champ :
# 4s = 4 octets bruts, H = uint16, I = uint32
HEADER = struct.Struct("<4sHHII")

# Q = uint64, d = float64, f = float32, B = uint8, 2x = 2 octets de padding
# timestamp, lat, lon, depth, roll, pitch, yaw, status, checksum, padding
RECORD = struct.Struct("<QddffffBB2x")

CHECKSUM_OFFSET = 41

# Codes de status
STATUS_OK = 0
STATUS_GPS_LOST = 1
STATUS_SENSOR_FAULT = 2

assert HEADER.size == 16
assert RECORD.size == 44


def compute_checksum(record_bytes):
    """Somme des octets 0 à 40, modulo 256."""
    return sum(record_bytes[:CHECKSUM_OFFSET]) & 0xFF


def pack_header(record_count):
    """Transforme l'en-tête en 16 octets."""
    return HEADER.pack(MAGIC, VERSION, RECORD.size, record_count, 0)


def pack_record(timestamp_us, lat, lon, depth, roll, pitch, yaw, status):
    """Transforme enregistrement en 44 octets, checksum inclus."""
    raw = bytearray(RECORD.pack(timestamp_us, lat, lon, depth,
                                roll, pitch, yaw, status, 0))
    raw[CHECKSUM_OFFSET] = compute_checksum(raw)
    return bytes(raw)