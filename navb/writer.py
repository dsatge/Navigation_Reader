"""Écriture fichiers NAVB."""
from navb.format import pack_header, pack_record


def write_navb(path, records):
	"""records : liste des vars
	(timestamp_us, lat, lon, depth, roll, pitch, yaw, status)."""
	with open(path, "wb") as f:	# wb -> écriture binaire
		f.write(pack_header(len(records)))
		for rec in records:
			f.write(pack_record(*rec))	# transforme les donnees en arguments