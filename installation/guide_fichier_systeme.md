# Guide Fichier Système & Matériel CAN

> [!TIP]
> L'assistant interactif `./install.sh` configure et installe automatiquement ces services selon votre matériel. Ce guide détaille la configuration manuelle.

## Dépendances Système 

```bash
sudo apt update
sudo apt install -y dfu-util can-utils
```

## Fichiers
Dans le dossier `installation/`, vous trouverez `etc/systemd/system/`
dans ce dossier il y a 3 services : 
- le can-wake.service, il sert a passer le bootloader du stm32 du modem can en mode normal.
- le can-usb.service sert a crée l'interface can0 sur le port usb du modem can.
> **Important** : utiliser le can-usb uniquement avec le firmware candlelight.

- le slcan.service sert a crée l'interface can0 sur le port usb du modem can.
> **Important** : utiliser le slcan uniquement avec le firmware slcan.