# ⚡ Guide d'Optimisation du Démarrage Rapide (Fast-Boot) — Raspberry Pi 5

> [!TIP]
> L'étape 6 de l'installateur interactif `./install.sh` permet de désactiver automatiquement les services lents au démarrage (Étape 3 ci-dessous). Les étapes 1 et 2 concernent l'EEPROM et le firmware et s'éditent manuellement.

Ce guide regroupe les étapes de configuration système et matérielle à effectuer sur un **Raspberry Pi 5** pour réduire son temps de démarrage au minimum (passage de ~31 secondes à ~19 secondes).

---

## 🛠️ 1. Configuration du Bootloader EEPROM

Par défaut, le bootloader du Raspberry Pi 5 teste les ports USB et le réseau avant de démarrer sur la carte SD. Nous forçons le démarrage direct et immédiat sur la carte SD.

Ouvrez la configuration de l'EEPROM :
```bash
sudo rpi-eeprom-config --edit
```

Remplacez ou ajustez les paramètres suivants dans le fichier :
```ini
[all]
BOOT_UART=0
POWER_OFF_ON_HALT=1
BOOT_ORDER=0xf1
PSU_MAX_CURRENT=5000
NET_INSTALL_AT_POWER_ON=0
```

* Sauvegardez avec `Ctrl + O` puis appuyez sur `Entrée`.
* Quittez avec `Ctrl + X`.

---

## ⚙️ 2. Configuration du Firmware et du CPU (`config.txt`)

Éditez le fichier de configuration du firmware Raspberry Pi :
```bash
sudo nano /boot/firmware/config.txt
```

Ajoutez ou modifiez les lignes suivantes dans la section `[all]` :
```ini
[all]
# Suppression du splash screen arc-en-ciel et des délais d'attente
disable_splash=1
boot_delay=0

# Fréquence CPU maximale dès les premières secondes
initial_turbo=30

# Overclocking du bus MicroSD compatible UHS-I
dtparam=sd_overclock=100

# Désactivation des sondes de détection caméra inutiles
camera_auto_detect=0

# Configuration graphique et noyau (indispensable sur Raspberry Pi 5)
auto_initramfs=1
dtoverlay=vc4-kms-v3d
display_auto_detect=1
```

* Sauvegardez avec `Ctrl + O` puis `Entrée`.
* Quittez avec `Ctrl + X`.

> [!CAUTION]
> Sur Raspberry Pi 5, veillez à toujours laisser **`auto_initramfs=1`**. Le pilote graphique 3D matériel (VC4/V3D) et la puce d'E/S RP1 en ont impérativement besoin au démarrage.

---

## 🧹 3. Désactivation des Services Linux Lents (`systemd`)

Par défaut, Raspberry Pi OS attend d'avoir une connexion réseau active avant de considérer le démarrage terminé, et lance des vérifications d'arrière-plan inutiles sur un système embarqué.

Exécutez ces commandes dans le terminal :

```bash
# 1. Ne plus bloquer l'affichage en attendant la connexion réseau
sudo systemctl disable NetworkManager-wait-online.service

# 2. Désactiver les tâches de maintenance et mises à jour quotidiennes en arrière-plan
sudo systemctl disable apt-daily.timer apt-daily-upgrade.timer man-db.timer

# 3. Désactiver le fichier d'échange swap lent et la vérification de màj EEPROM
sudo systemctl disable dphys-swapfile.service
sudo systemctl disable rpi-eeprom-update.service
```

---

## 🔄 4. Appliquer les Changements

Une fois ces étapes réalisées, redémarrez complètement votre Raspberry Pi pour appliquer l'ensemble des optimisations :

```bash
sudo reboot
```

---

## 🔍 Vérification du Temps de Démarrage (Optionnel)

Après le redémarrage, vous pouvez mesurer le temps exact de démarrage avec la commande :
```bash
systemd-analyze
```
