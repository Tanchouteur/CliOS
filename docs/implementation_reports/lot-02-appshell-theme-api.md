# Lot 02 — AppShell et Theme API v1

## Ce qui change concrètement pour toi

Les cinq thèmes ouvrent les mêmes réglages et utilisent les mêmes confirmations.
Le retour ramène au cockpit. Au-dessus de 5 km/h, une bannière reste visible sans
bloquer les actions, qui conservent leur confirmation et sont journalisées avec
la vitesse.

## Ce que tu dois faire

Pour créer ou maintenir un thème, émettre `settingsRequested(route)` et
`commandRequested(command)`. Un thème officiel ne doit jamais appeler `bridge`
directement.

## Développement et livraison

Les routes communes sont `home`, `appearance`, `vehicle`, `services`, `system`,
`diagnostic` et `developer`. Un manifeste doit déclarer Theme API v1, la version
CliOS minimale, les capacités et la résolution 1920×720.

## Compatibilité et retour arrière

Les anciens thèmes ne sont pas adaptés automatiquement. Un thème incompatible
produit un diagnostic et GT Modern est chargé en secours. Le QML local est du
code de confiance non sandboxé et n’est accepté qu’en mode développeur.

## Vérifications réalisées

Les sept routes sont chargées pour Apex, Atelier Luxe, GT Modern, JDM Mugen et
Legacy ; les thèmes officiels sont contrôlés sans référence directe à `bridge`.
