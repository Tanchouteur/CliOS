# Politique de sécurité

Ce document définit les protocoles de signalement et les engagements de maintenance concernant la sécurité de ce logiciel.

## 1. Versions supportées

La maintenance de sécurité est assurée exclusivement sur la branche principale (`main`). Les versions obsolètes ou de développement ne font pas l'objet d'un suivi actif.

| Version | Supportée |
| ------- | --------- |
| Latest  | ✅ Oui    |
| < 1.0   | ❌ Non    |

## 2. Signalement d'une vulnérabilité

La divulgation publique d'une faille de sécurité est proscrite afin de protéger les utilisateurs du système. Pour signaler une vulnérabilité, veuillez suivre la procédure suivante :

1. Ne pas ouvrir d'Issue publique.
2. Envoyer un rapport détaillé par courriel à : **[VOTRE_EMAIL_ICI]**
3. Inclure dans le rapport :
   - La nature de la faille (Injection, élévation de privilèges, déni de service, etc.).
   - Le vecteur d'attaque et les composants affectés (ex: API, service CAN).
   - Un exemple de preuve de concept (PoC) ou les étapes de reproduction.

## 3. Processus de traitement

Dès réception d'un signalement valide :
- Un accusé de réception est envoyé sous 48 heures ouvrées.
- Une analyse d'impact est réalisée pour évaluer la criticité du risque.
- Un correctif est développé et déployé sur la branche `main`.
- Une annonce officielle est publiée dans l'onglet "Announcements" une fois le risque neutralisé.

Nous sollicitons la patience de la communauté pendant le cycle de correction avant toute divulgation publique.
