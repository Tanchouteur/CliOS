# ⚡ Guide d'Optimisation du Démarrage Rapide (Fast-Boot) — Raspberry Pi 5

> [!TIP]
> L'étape 6 de `./install.sh` propose séparément les services de fond, le mode
> kiosque sans LightDM et la désactivation de cloud-init. Elle conserve toujours
> NetworkManager, Bluetooth, Avahi, SSH, USB, CAN et l'updater CliOS.

Ce guide regroupe les étapes de configuration système et matérielle à effectuer sur un **Raspberry Pi 5**. Mesurez chaque modification : le temps utile est celui du premier frame CliOS, pas seulement celui où une cible systemd devient active.

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

N'ajoutez pas `initial_turbo` ou d'overclocking de la carte SD sans validation
matérielle. Après toute modification, vérifiez la température et les alertes avec
`vcgencmd get_throttled`.

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

# 4. Kiosque autonome : ne pas lancer un second gestionnaire graphique
sudo systemctl disable lightdm.service
sudo systemctl set-default multi-user.target
```

CliOS doit rester rattaché à `multi-user.target`. Remplacer son `WantedBy` par
`basic.target` ne le rend pas prêt plus tôt : cette directive choisit qui active
le service, elle ne supprime pas ses contraintes d'ordre et de session.

Lorsque la machine est définitivement provisionnée, cloud-init peut être
désactivé de manière réversible :

```bash
sudo touch /etc/cloud/cloud-init.disabled
```

Ne faites pas cette opération sur une image dont la création du compte, les clés
SSH ou le réseau dépendent encore du premier démarrage cloud-init.

Pour revenir à la configuration de bureau :

```bash
sudo systemctl set-default graphical.target
sudo systemctl enable lightdm.service NetworkManager-wait-online.service
sudo rm -f /etc/cloud/cloud-init.disabled
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
systemd-analyze critical-chain clios.service
systemctl show clios.service -p ActiveEnterTimestampMonotonic -p NRestarts
journalctl -b -u clios.service -o short-monotonic --no-pager
```
