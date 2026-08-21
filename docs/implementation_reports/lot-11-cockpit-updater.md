# Lot 11 — Mise à jour dans le cockpit

## Ce qui change concrètement pour toi

La page Système montre un état unique parmi `IDLE`, `CHECKING`, `AVAILABLE`,
`DOWNLOADING`, `STAGED`, `ACTIVATING`, `UP_TO_DATE` et `ERROR`, avec versions,
progression et cause lisible.

## Comportement

Le retour d'Internet déclenche une recherche discrète au plus une fois par 24 h.
Le bouton manuel recherche toujours ; aucun téléchargement n'est automatique.
Activation et rollback utilisent le dialogue commun. Au-dessus de 5 km/h, la
bannière reste visible, la confirmation est obligatoire et la vitesse est
journalisée sans blocage forcé.

## Diagnostic

L'état courant, le dernier manifeste et l'erreur structurée sont inclus dans le
snapshot du bundle diagnostic.
