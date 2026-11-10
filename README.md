# Navigation_Reader : lecture, écriture et validation de données de navigation binaires
 
Projet personnel en **Python** (puis **C++**) autour d'une problématique industrielle classique en navigation embarquée :
 
> **Comment lire et écrire efficacement des données de navigation enregistrées dans un format binaire, et de combien peut-on accélérer un lecteur Python naïf sans perdre en conformité ?**
 
---
 
## 1. Contexte et enjeux
 
### D'où viennent ces données ?
 
Les systèmes de navigation embarqués (centrales inertielles de navires, sous-marins, drones marins…) calculent en permanence la **position**, la **profondeur** et l'**orientation** d'un engin. Pour valider leurs algorithmes, les ingénieurs :
 
1. font naviguer l'engin (en mer ou sur un banc de test) ;
2. **enregistrent** tout ce que l'appareil mesure et calcule, des centaines de fois par seconde, pendant des heures ;
3. **relisent ces enregistrements** avec des outils (souvent en Python) pour vérifier les résultats : dérive, erreurs, comparaison entre deux versions d'un algorithme.
### Pourquoi un format binaire ?
 
Un appareil embarqué n'écrit pas de texte lisible (CSV, JSON) : ce serait trop volumineux et trop lent pour un petit processeur. Il écrit les valeurs **brutes, octet par octet**, dans un ordre fixé par une **spécification**. Le fichier est compact et rapide à produire, mais illisible sans cette spécification.
 
### Le problème
 
Un lecteur Python « naïf », qui traite les enregistrements un par un dans une boucle, est **correct mais lent** : chaque enregistrement crée plusieurs objets Python. Sur des millions d'enregistrements, la lecture peut prendre des minutes. Comme ces outils sont relancés des dizaines de fois en validation, cette lenteur coûte cher.
 
### Objectifs du projet
 
| Objectif | Mise en œuvre |
|---|---|
| Définir un format binaire et sa spécification | Format **NAVB** (section 3) |
| Écrire dans ce format | Module `navb/writer.py` |
| Produire des données réalistes | Simulateur de drone sous-marin (section 4) |
| Lire le format de façon fiable | Lecteur de référence en Python pur *(à venir)* |
| Accélérer la lecture | Lecteur numpy, puis module C++ avec wrapper Python (pybind11) *(à venir)* |
| Prouver la conformité | Tests unitaires pytest comparant les lecteurs *(à venir)* |
| Mesurer les gains | Benchmark *(à venir)* |
 
---
 
## 2. État d'avancement
 
- [x] Spécification du format NAVB
- [x] Écriture de fichiers NAVB
- [x] Simulateur de navigation (données cohérentes + pertes GPS)
- [x] Génération de fichiers volontairement corrompus (pour les tests)
- [ ] Lecteur v1 : Python pur (référence)
- [ ] Lecteur v2 : numpy
- [ ] Lecteur v3 : C++ + pybind11, avec vérification du checksum
- [ ] Tests unitaires et de conformité (pytest)
- [ ] Benchmark et analyse des résultats
---
 
## 3. Le format NAVB (version 1)
 
Toutes les valeurs sont en **little-endian**. Un fichier est composé d'un **en-tête** suivi de `record_count` **enregistrements** de taille fixe.
 
### En-tête (16 octets)
 
| Octets | Champ | Type | Description |
|---|---|---|---|
| 0–3 | `magic` | 4 octets | Toujours `b"NAVB"` : identifie le format |
| 4–5 | `version` | uint16 | Version du format (1) |
| 6–7 | `record_size` | uint16 | Taille d'un enregistrement (44) |
| 8–11 | `record_count` | uint32 | Nombre d'enregistrements |
| 12–15 | `reserved` | uint32 | Réservé (0) |
 
### Enregistrement (44 octets)
 
| Octets | Champ | Type | Unité |
|---|---|---|---|
| 0–7 | `timestamp_us` | uint64 | microsecondes depuis le 01/01/1970 |
| 8–15 | `lat` | float64 | degrés |
| 16–23 | `lon` | float64 | degrés |
| 24–27 | `depth` | float32 | mètres |
| 28–31 | `roll` | float32 | degrés (roulis) |
| 32–35 | `pitch` | float32 | degrés (tangage) |
| 36–39 | `yaw` | float32 | degrés (cap) |
| 40 | `status` | uint8 | 0 = OK, 1 = GPS perdu, 2 = défaut capteur |
| 41 | `checksum` | uint8 | somme des octets 0 à 40, modulo 256 |
| 42–43 | *padding* | — | octets de remplissage |
 
Taille d'un fichier : `16 + record_count × 44` octets.
 
### Choix techniques
 
- **Timestamp en `uint64` (microsecondes)** : un `uint32` déborderait au bout d'environ 71 minutes en microsecondes. Un entier garantit une précision exacte, contrairement à un flottant sur des valeurs aussi grandes.
- **Latitude et longitude en `float64`** : la double précision est nécessaire pour une position au centimètre près.
- **Angles et profondeur en `float32`** : une précision suffisante, et un enregistrement plus compact.
- **Checksum par enregistrement** : il permet de détecter un enregistrement corrompu sans rejeter tout le fichier.
- **Taille d'enregistrement fixe (44 octets)** : l'enregistrement *n* se trouve directement à l'offset `16 + n × 44`.
---
 
## 4. Simulation de navigation
 
Pour disposer de données sans matériel réel, `generator.py` simule un **drone sous-marin** qui enregistre sa navigation à **100 Hz**.
 
### Modèle de trajectoire
 
| Grandeur | Modèle |
|---|---|
| Fréquence | 100 Hz : un enregistrement toutes les 10 ms (`t = i / FREQ_HZ`) |
| Trajectoire | Cercle de **200 m** de rayon autour d'un point au large de Caen (49,30° N ; 0,35° O) |
| Vitesse | **2 m/s**, soit une vitesse angulaire `ω = v / r = 0,01 rad/s` (un tour en environ 10 min 30) |
| Position | `x = R·cos(ωt)`, `y = R·sin(ωt)` en mètres, convertis en degrés (1° de latitude ≈ 111 320 m) |
| Profondeur | Oscillation autour de 10 m : `10 + 5·sin(t / 30)`, plus un bruit gaussien |
| Cap (`yaw`) | Tangent au cercle |
| Roulis / tangage | Petites valeurs bruitées (le drone penche dans le virage) |
| Statut | `GPS perdu` sur environ 0,1 % des enregistrements, `OK` sinon |
 
### Données cohérentes et données en erreur
 
Le projet distingue deux types d'« erreurs » :
 
1. **Des données valides mais signalées** : par exemple une perte de GPS, indiquée par le champ `status`. Le fichier reste conforme au format. C'est le **générateur** qui les produit.
2. **Des fichiers corrompus** : un octet abîmé, un fichier tronqué, un en-tête invalide. Ils sont fabriqués **à part**, à partir d'un fichier valide, par `navb/corrupt.py`. On contrôle ainsi précisément l'erreur testée.
### Reproductibilité
 
Le générateur utilise un générateur pseudo-aléatoire dédié (`random.Random(seed)`). **Avec la même graine (seed), on obtient exactement le même fichier, octet pour octet.** Les tests et le benchmark sont donc reproductibles.
 
---
 
## 5. Installation
 
Prérequis : **Python 3.10+**.
 
```bash
git clone https://github.com/dsatge/Navigation_Reader.git
cd Navigation_Reader
python3 -m venv .venv
source .venv/bin/activate
pip install numpy pytest
```
 
---
 
## 6. Générer des données
 
### Générer un fichier de navigation
 
```bash
python3 generator.py <fichier_de_sortie> [-n NOMBRE] [--seed GRAINE]
```
 
| Option | Rôle | Défaut |
|---|---|---|
| `fichier_de_sortie` | Chemin du fichier `.navb` à créer | *(obligatoire)* |
| `-n`, `--count` | Nombre d'enregistrements | 100 000 |
| `--seed` | Graine aléatoire (même graine = même fichier) | 42 |
 
**Exemples :**
 
```bash
# Petit fichier pour les tests : 1 000 enregistrements = 10 s de navigation
python3 generator.py data/petit.navb -n 1000
 
# Gros fichier pour le benchmark : 1 000 000 d'enregistrements ≈ 2 h 47 de navigation
python3 generator.py data/gros.navb -n 1000000
 
# Un autre jeu de données, avec une autre graine
python3 generator.py data/autre.navb -n 1000 --seed 7
```
 
Durée simulée = `nombre d'enregistrements / 100` secondes.
 
### Vérifier le fichier généré
 
```bash
# Taille attendue : 16 + n × 44 octets (ex. 44 016 octets pour n = 1000)
ls -l data/petit.navb
 
# Afficher les premiers octets : "NAVB" doit apparaître au début
xxd data/petit.navb | head -4
```
 
### Générer des fichiers corrompus
 
Les fonctions de `navb/corrupt.py` prennent un fichier valide et en écrivent une copie abîmée :
 
| Fonction | Erreur simulée |
|---|---|
| `flip_byte(src, dst, record_index)` | Un octet de l'enregistrement `record_index` est inversé : le checksum ne correspond plus |
| `truncate(src, dst, remove_bytes=10)` | La fin du fichier est coupée (enregistrement interrompu) |
| `bad_magic(src, dst)` | L'en-tête ne commence plus par `NAVB` |
 
```bash
python3 -c "from navb.corrupt import flip_byte; flip_byte('data/petit.navb', 'data/checksum_ko.navb', 5)"
python3 -c "from navb.corrupt import truncate; truncate('data/petit.navb', 'data/tronque.navb')"
python3 -c "from navb.corrupt import bad_magic; bad_magic('data/petit.navb', 'data/magic_ko.navb')"
```
 
Ces fichiers serviront à vérifier que les lecteurs **détectent les erreurs et lèvent une exception claire**.
 
---
 
## 7. Structure du projet
 
```
Navigation_Reader/
├── generator.py        # Simulateur de drone : génère un fichier NAVB
├── navb/
│   ├── __init__.py
│   ├── format.py       # Spécification du format (en-tête, enregistrement, checksum)
│   ├── writer.py       # Écriture de fichiers NAVB
│   └── corrupt.py      # Fabrication de fichiers corrompus pour les tests
├── tests/              # Tests pytest (à venir)
└── data/               # Fichiers générés (non versionnés)
```
 
---
 
## 8. Prochaines étapes
 
1. **Lecteur v1 (Python pur)** : lecture enregistrement par enregistrement avec `struct`. Il servira de **référence de conformité**.
2. **Lecteur v2 (numpy)** : lecture du fichier en un seul bloc avec un `dtype` structuré, sans boucle Python.
3. **Lecteur v3 (C++ + pybind11)** : boucle compilée qui décode et **vérifie le checksum** en un seul passage, appelée depuis Python.
4. **Tests** : conformité des trois lecteurs entre eux, et détection des fichiers corrompus.
5. **Benchmark** : temps de lecture et facteur d'accélération sur 1 000 000 d'enregistrements.
 
