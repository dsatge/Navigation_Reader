"""Simule un drone sous-marin / enregistre sa nav"""
import argparse
import math
import random

from navb.format import STATUS_OK, STATUS_GPS_LOST
from navb.writer import write_navb

FREQ_HZ = 100					# 100 enregistrements par seconde
CENTER_LAT = 49.30				# au large de Caen
CENTER_LON = -0.35
RADIUS_M = 200.0				# rayon du cercle
SPEED_MS = 2.0					# vitesse du drone
M_PER_DEG_LAT = 111_320.0		# 1° de latitude ≈ 111 km
START_US = 1_762_300_000_000_000


def generate_records(count, seed=42, gps_loss_rate=0.001):
	rng = random.Random(seed)
	m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(CENTER_LAT))
	omega = SPEED_MS / RADIUS_M			# vitesse angulaire (vitesse/rayon)

	records = []
	for i in range(count):
		t = i / FREQ_HZ					# temps en secondes
		angle = omega * t

		# Position sur cercle, en metres puis convertie en degrés
		x_east = RADIUS_M * math.cos(angle)
		y_north = RADIUS_M * math.sin(angle)
		lat = CENTER_LAT + y_north / M_PER_DEG_LAT
		lon = CENTER_LON + x_east / m_per_deg_lon

		depth = 10.0 + 5.0 * math.sin(t / 30.0) + rng.gauss(0, 0.05)
		yaw = (90.0 - math.degrees(angle + math.pi / 2)) % 360   # cap en degrés
		roll = -5.0 + rng.gauss(0, 0.2)	# inclinaison du virage
		pitch = rng.gauss(0, 0.3)

		status = STATUS_GPS_LOST if rng.random() < gps_loss_rate else STATUS_OK
		timestamp_us = START_US + i * (1_000_000 // FREQ_HZ)   # +10 ms à chaque fois

		records.append((timestamp_us, lat, lon, depth, roll, pitch, yaw, status))
	return records


def main():
	parser = argparse.ArgumentParser(description="Génère un fichier NAVB simulé.")
	parser.add_argument("output", help="chemin du fichier à créer")
	parser.add_argument("-n", "--count", type=int, default=100_000)
	parser.add_argument("--seed", type=int, default=42)
	args = parser.parse_args()

	records = generate_records(args.count, args.seed)
	write_navb(args.output, records)
	print(f"{args.count} enregistrements écrits dans {args.output}")


if __name__ == "__main__":
	main()