# Os qui va tourner sur un rasberry dans ma clio pour faire un dashboard qui centralise les données de la voiture et les affiche sur un écran tactile
## 🚀 Roadmap & Avancement du Projet

Légende :
- ✅ **Terminé** : Fonctionnalité implémentée et stable.
- 🟧 **En cours** : En cours de développement ou nécessite des corrections (bugs).
- ⬜ **À faire** : Idée validée, développement à venir.

### ✅ Terminé
* ✅ **Moteur CAN Moteur** : Lecture et décodage du bus CAN principal.
* ✅ **Système de son moteur synthétique** : Génération audio dynamique incluant le sifflement et l'aspiration du turbo basés sur les RPM et le couple ECU.
* ✅ **Gestion multi-véhicules** : Création de profils de voitures avec des fichiers de sauvegarde isolés (`save_[id].json`) et changement à chaud depuis l'interface.
* ✅ **Système de notifications** : Alertes système et conduite (ex: avertissement si embrayage enfoncé plus de 5 secondes).
* ✅ **Scanner OBD** : Lecture des codes défauts.
* ✅ **Paramétrage des services** : Configuration individuelle et persistante pour chaque module du système.
* ✅ **Télémétrie de session** : Enregistrement des données du trajet en cours.
* ✅ **Analyse de fréquences** : Détection des requêtes donnant les mesures les plus élevées.
* ✅ **Calculateur de coût de trajet** : Estimation financière basée sur la consommation et le prix du carburant.
* ✅ **Sonomètre** : Mesure du bruit ambiant dans l'habitacle.
* ✅ **Interface de Debug** : Affichage en direct de l'intégralité des trames lues sur le bus CAN et de leurs valeurs décodées.

### 🟧 En cours / À stabiliser
* 🟧 **Gestion de l'éclairage de l'habitacle** : Contrôle des LEDs ou lumières intérieures.
* 🟧 **Intégration IMU** : Exploitation de la centrale à inertie (accélération, g-force, inclinaison).
* 🟧 **Simulateur (Mock) avancé** : Création d'un générateur de données de roulage cohérentes, incluant un contrôle manuel (ex: forcer le throttle à 50% pour simuler une accélération).
* 🟧 **Monitoring Système** : Système de calcul de l'empreinte processeur (CPU/RAM) de chaque service en temps réel.

### 💡 À faire / Boîte à idées
* ⬜ **Moteur CAN Habitacle** : Interfaçage avec le réseau secondaire du véhicule (confort, multimédia).
* ⬜ **Dashcam intégrée** : Enregistrement vidéo synchronisé avec la télémétrie.
* ⬜ **Télémétrie Cloud** : Envoi et stockage distant des trajets, avec génération de statistiques globales (RPM moyen, vitesse max, historique des rapports).
* ⬜ **Luminosité adaptative ☀️** : Gestion automatique du rétroéclairage de l'écran en utilisant les capteurs de luminosité d'origine via le bus CAN.
* ⬜ **Indicateur de dissipation d'énergie** : Calcul de l'argent "perdu" lors des phases de freinage (énergie dissipée en chaleur).
* ⬜ **Coût instantané (€/min)** : Affichage de la consommation financière en temps réel, équivalent à la consommation instantanée en L/100km.