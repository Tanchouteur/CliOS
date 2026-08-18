# Nouveau Dashboard "Apex" — Effet Waouh 3D Animé

## Résumé

Création d'un **3ème dashboard** nommé **"Apex"** pour CliOS, avec un design ultra-premium, des effets 3D (perspective, profondeur, ombres portées), des animations constantes (particules, pulsations, respiration des composants), et une ergonomie tactile optimisée pour l'écran 12,3" 1920×720 en console centrale.

## Contraintes techniques

| Contrainte | Impact design |
|---|---|
| **1920×720 px** (12,3") | Format ultra-wide — layout horizontal, pas de scroll vertical |
| **Exclusivement tactile** | Boutons ≥ 60px, zones de touch larges, pas de hover |
| **USB = faible luminosité** | Couleurs vives sur fond très sombre, pas de texte gris clair subtil, contraste maximal |
| **Console centrale** | Visible des deux côtés, info condensée, lisible en coup d'œil |
| **QML / PySide6** | Utilisation de Canvas, ShaderEffect, transformations 3D natives QML |

## Philosophie de design

- **Minimaliste mais vivant** : moins d'infos que le GT actuel (pas de 3 colonnes surchargées), mais chaque élément est animé, texturé, en relief
- **3D par perspective** : les cartes ont une légère rotation 3D au repos, les jauges sont rendues avec des arcs en relief
- **Animations constantes** :
  - Particules de lumière qui flottent en fond (Canvas animé)
  - Pulsation de la vitesse synchronisée avec le rythme moteur
  - Barre RPM avec flammes/lueur qui monte
  - Respiration des bordures de cartes (glow qui pulse)
  - Jauge carburant avec effet liquide ondulant
  - Transitions fluides entre valeurs (Behavior on + easing)
- **Pas de menu complexe** : navigation ultra-simple en bas, 3 onglets max (Conduite / Perf / Menu)

## Architecture des fichiers

### Vue principale
#### [NEW] [ApexDash.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/views/ApexDash.qml)
Le layout principal du dashboard Apex. Structure :
- **Fond animé** : Canvas avec particules de lumière flottantes
- **Barre d'état** minimaliste en haut (48px) : heure, température, voyants, état USB
- **Zone centrale** (624px) : divisée en layout adaptatif selon la page
- **Navigation tactile** en bas (48px) : 3 boutons avec effet de sélection 3D

---

### Composants 3D & animés

#### [NEW] [ApexSpeedometer.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/components/ApexSpeedometer.qml)
Compteur de vitesse central avec :
- Arc circulaire rendu en Canvas avec dégradé
- Chiffre central géant (police DIN Condensed) qui pulse subtilement avec le RPM
- Effet de lueur (glow) autour du chiffre, couleur liée au RPM
- Aiguille animée avec traînée lumineuse
- Unité "km/h" en petit sous le chiffre

#### [NEW] [ApexRpmBar.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/components/ApexRpmBar.qml)
Barre de RPM horizontale panoramique :
- Toute la largeur de l'écran, fine (20px), sous la barre d'état
- Segments animés qui s'allument de gauche à droite
- Couleur qui passe de cyan → ambre → rouge
- Effet de lueur/flamme quand on approche de la redline
- Pulsation à haute fréquence en zone rouge

#### [NEW] [ApexCard3D.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/components/ApexCard3D.qml)
Carte avec effet 3D au repos :
- Légère perspective (transform.matrix4x4) pour donner de la profondeur
- Bordure avec glow qui pulse lentement (respiration)
- Fond avec gradient subtil et texture de bruit
- Ombre portée dynamique
- Animation d'entrée (slide + fade + rotation)

#### [NEW] [ApexGauge.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/components/ApexGauge.qml)
Jauge circulaire réutilisable :
- Arc en Canvas avec dégradé et anti-aliasing
- Reflet 3D (highlight en haut de l'arc)
- Animation fluide des valeurs
- Tick marks avec profondeur (alternance clair/sombre)

#### [NEW] [ApexFuelWave.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/components/ApexFuelWave.qml)
Jauge de carburant avec effet liquide :
- Forme de réservoir stylisée
- Surface du liquide qui ondule (Canvas animé, sinusoïde)
- Couleur qui change selon le niveau (cyan → ambre → rouge)
- Bulles qui montent dans le liquide

#### [NEW] [ApexParticles.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/components/ApexParticles.qml)
Fond de particules animées :
- Points lumineux qui flottent lentement
- Taille et opacité variables
- Mouvement organique (Perlin-like via sin/cos combinés)
- Couleur liée au thème (bleu/cyan par défaut)
- Faible densité pour ne pas gêner la lisibilité

#### [NEW] [ApexNavBar.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/components/ApexNavBar.qml)
Barre de navigation tactile 3D :
- 3 boutons : CONDUITE / PERF / MENU
- Bouton sélectionné avec effet "enfoncé" (perspective inversée)
- Transition de sélection avec lueur
- Zone tactile ≥ 60px de haut

#### [NEW] [ApexStatusBar.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/components/ApexStatusBar.qml)
Barre d'état ultra-minimaliste :
- Heure en gros, température, voyants actifs seulement
- Badge USB discret
- Pas de texte "CliOS GT" qui prend de la place
- Fond semi-transparent avec blur (si supporté)

---

### Pages

#### [NEW] [ApexDrivePage.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/pages/ApexDrivePage.qml)
Page de conduite principale :
- **Centre** : compteur de vitesse géant (ApexSpeedometer)
- **Gauche** : rapport de vitesse en très gros + carburant (ApexFuelWave)
- **Droite** : température moteur (ApexGauge) + conso instantanée
- La barre RPM est toujours visible en haut
- Toutes les valeurs avec Behavior on pour transitions fluides

#### [NEW] [ApexPerfPage.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/pages/ApexPerfPage.qml)
Page performance :
- 3 ApexCard3D en row : Puissance / Couple / Régime
- Chaque carte avec valeur géante animée + jauge
- Statistiques session en bas dans des métriques compactes

#### [NEW] [ApexMenuPage.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/pages/ApexMenuPage.qml)
Menu simplifié :
- Grille 2×3 de cartes 3D cliquables
- Apparence, Véhicule, Services, Système, Développeur, Quitter
- Animation d'entrée en cascade (staggered)

---

### Intégration

#### [MODIFY] [qmldir](file:///Users/louis/PycharmProjects/CliOS/frontend/views/qmldir)
Ajout de l'entrée `ApexDash` pour le nouveau dashboard.

#### [MODIFY] [StyleManager.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/style/StyleManager.qml)
Ajout de la logique de sélection du dashboard "apex" et de la source correspondante.

#### [MODIFY] [GtAppearancePage.qml](file:///Users/louis/PycharmProjects/CliOS/frontend/pages/GtAppearancePage.qml)
Ajout de l'option "Apex" dans la liste des dashboards sélectionnables.

## Palette de couleurs Apex

Conçue pour un écran USB faible luminosité — **contraste maximal, couleurs vives sur noir profond** :

| Rôle | Couleur | Hex |
|---|---|---|
| Fond principal | Noir profond | `#050709` |
| Surface card | Gris charbon | `#0E1216` |
| Surface élevée | Gris acier | `#161B22` |
| Accent primaire | Cyan électrique | `#00E5FF` |
| Accent chaud | Ambre vif | `#FFB300` |
| Danger | Rouge néon | `#FF1744` |
| Succès | Vert émeraude | `#00E676` |
| Texte principal | Blanc pur | `#FFFFFF` |
| Texte secondaire | Gris clair | `#B0BEC5` |
| Lueur / glow | Cyan translucide | `rgba(0, 229, 255, 0.15)` |

## Animations constantes (le dashboard "vit")

| Élément | Animation | Durée |
|---|---|---|
| Particules de fond | Float organique continu | ∞ (60fps Canvas) |
| Glow des cartes | Pulsation opacité 0.08→0.25 | 3000ms ease |
| Chiffre vitesse | Pulsation taille ±2% liée RPM | 800ms |
| Barre RPM | Segments qui s'allument séquentiellement | 100ms/seg |
| Jauge carburant | Ondulation surface liquide | 2000ms |
| Valeurs numériques | Behavior on avec easing OutCubic | 300ms |
| Transitions de page | Slide + fade + légère rotation 3D | 350ms |
| Nav sélection | Glow expand + couleur transition | 200ms |
| Bordure RPM zone rouge | Flash pulsatoire rapide | 200ms |

## Effets 3D (sans WebGL, pur QML)

1. **Perspective sur les cartes** : `transform: Matrix4x4 { ... }` avec légère rotation Y
2. **Ombres portées** : `layer.effect: DropShadow` sur les cartes
3. **Relief sur les jauges** : gradient linéaire simulant un éclairage directionnel
4. **Profondeur de la nav** : bouton actif "enfoncé" via scale + shadow inversée
5. **Parallaxe particules** : 2 couches de particules à vitesses différentes

## Vérification

### Tests visuels
- Lancer `python3 -u main.py --ui gui --mock` et sélectionner le dashboard "Apex" dans Apparence
- Vérifier que toutes les animations tournent à 60fps
- Vérifier la lisibilité sur fond sombre
- Tester la navigation tactile (3 onglets)
- Vérifier les transitions de page

### Tests fonctionnels
- Vérifier que toutes les données du bridge sont correctement affichées
- Tester les actions (pause/fin trajet, RAZ trip, etc.)
- Vérifier la bascule entre dashboards (GT ↔ Apex)
