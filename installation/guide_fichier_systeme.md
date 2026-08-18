# Guide Fichier

## Python
il faut installer les outils systeme manquant : 

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