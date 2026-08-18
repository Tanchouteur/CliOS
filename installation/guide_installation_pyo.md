# Guide d'installation : Pyo & Environnement Python sur Raspberry Pi

Guide pas-à-pas pour reconfigurer un environnement virtuel propre et compiler `pyo` sans erreurs de compilation GCC ni problèmes de permissions.

---

## 1. Dépendances système C & Audio

Installer les paquets de compilation et les bibliothèques C indispensables (en particulier `libportmidi-dev` et `liblo-dev` pour les headers C) :

```bash
sudo apt update && sudo apt install -y \
    build-essential \
    python3-dev \
    python3-venv \
    portaudio19-dev \
    libsndfile1-dev \
    liblo-dev \
    libjack-jackd2-dev \
    libportmidi-dev
```

---

## 2. Création de l'environnement virtuel (.venv)

> **Important** : Ne jamais utiliser `sudo` pour manipuler le venv.

```bash
# 1. Supprimer un ancien venv corrompu si existant
rm -rf .venv

# 2. Créer un venv propre
python3 -m venv .venv

# 3. Activer l'environnement
source .venv/bin/activate

# 4. Mettre à niveau pip, setuptools et wheel
pip install --upgrade pip setuptools wheel
```

---

## 3. Compilation et installation de Pyo

Sous Python 3.13+ et GCC 14+, l'option `-Wno-incompatible-pointer-types` est requise pour éviter les blocages sur les pointeurs de `liblo` :

```bash
CFLAGS="-Wno-incompatible-pointer-types -Wno-error" pip install --no-build-isolation pyo~=1.0.5
```

### Alternative (sans OSC / liblo)
Si le protocole OSC n'est pas utilisé dans le projet :

```bash
pip install --no-binary :all: --config-settings="--build-option=--no-osc" pyo~=1.0.5
```

---

## 4. Installation des autres dépendances

Une fois `pyo` compilé et installé avec succès :

```bash
pip install -r requirements.txt
```

---

## 5. Validation rapide

Vérifier que le module C de `pyo` et le sous-système audio s'exécutent sans erreur :

```bash
python -c "import pyo; print(f'Succès : pyo {pyo.PYO_VERSION} est opérationnel')"
```
