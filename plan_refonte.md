# Refonte graphique complète « CliOS GT »

  ## Résumé

  Transformer l’interface actuelle en un système automobile OEM cohérent, conçu pour l’écran tactile IPS 12,3″ de 1920×720 placé dans la console centrale.

  - Identité 100 % CliOS : suppression du mélange BMW/Renault, des emojis et des styles desktop.
  - Style par défaut gt_modern : graphite mat, contraste élevé, blanc franc et accent lumineux discret.
  - Catalogue extensible de styles installés sous `frontend/styles`, avec GT moderne et l’ancien dashboard comme paquets autonomes.
  - Toutes les informations et fonctions existantes restent accessibles.
  - À plus de 5 km/h, les pages complexes restent accessibles mais déclenchent une alerte non bloquante.
  - Aucun ajout Spotify, Waze, compte utilisateur ou dépendance réseau. Le routeur central sera seulement extensible pour les accueillir plus tard.
  - L’ergonomie suivra les principes automobiles de lisibilité immédiate et de limitation des distractions : informations assimilables rapidement, interactions cohérentes et grandes zones tactiles. Google
    Design for Driving (https://developers.google.com/cars/design/design-foundations/interaction-principles), principes visuels automobiles
    (https://developers.google.com/cars/design/design-foundations/visual-principles?authuser=19).

  ## Architecture visuelle

  ┌──────────────────── Barre d’état et voyants — 56 px ────────────────────┐
  │ heure / température │ clignotants + alertes │ USB / services / session │
  ├──── Conduite 330 px ─┬────── Contenu contextuel 1260 px ─┬─ Moteur 330 ┤
  │ vitesse              │ Conduite / Trajet / Performance    │ rapport     │
  │ régulateur            │ Diagnostic / menus et réglages     │ régime      │
  │ carburant/autonomie   │                                    │ température │
  │ trip/consommation     │                                    │ moteur      │
  ├──────────────────── Navigation tactile — 84 px ─────────────────────────┤
  │ Conduite │ Trajet │ Performance │ Diagnostic │ Menu                     │
  └──────────────────────────────────────────────────────────────────────────┘

  - Les panneaux latéraux restent visibles sur toutes les pages : vitesse, régulateur, carburant, autonomie, rapport, RPM et température moteur ne disparaissent jamais.
  - La barre supérieure remplace les pills techniques actuelles. Elle affiche les voyants utiles — clignotants, feux, frein, ceinture, portes, huile, batterie, ABS/ESP et moteur — puis uniquement les
    anomalies de services. L’état USB reste toujours visible, avec une alerte explicite en mode RAM non persistant.

  - La navigation inférieure utilise cinq cibles tactiles d’au moins 72×72 px, espacées d’au moins 16 px. Aucun survol ne sera nécessaire.
  - Les pages profondes restent dans la zone centrale avec un en-tête et un bouton retour homogènes.
  - Une action destructive — extinction, redémarrage, fin de trajet, remise à zéro — passe par une confirmation plein écran.
  - Les animations durent 120–250 ms. Les animations permanentes ou clignotantes sont réservées aux clignotants, à l’enregistrement et aux alertes critiques.

  ## Système graphique et interfaces

  - Créer un StyleManager QML avec un registre de styles. Chaque style fournit les couleurs sémantiques, typographies, espacements, rayons, épaisseurs, durées et paramètres de jauges.
  - Ajouter la configuration persistante ui.visual_style. `gt_modern` reste la valeur par défaut ; les autres identifiants sont découverts depuis les manifestes installés.

  - Le changement de style est immédiat et utilise le slot existant bridge.save_setting("ui.visual_style", styleId) ; aucun redémarrage n’est nécessaire.
  - Conserver theme.main comme couleur d’accent. Elle ne recolore que les sélections, progressions et détails lumineux. Une couleur UI dérivée impose une luminosité minimale pour rester lisible malgré le
    manque de puissance lumineuse de l’écran.

  - Standardiser la palette GT : fond #080B0F, surfaces opaques #11171D/#182029, texte principal #F4F7FA, texte secondaire au contraste renforcé, rouge danger, ambre avertissement et vert confirmation.
  - Utiliser une seule famille typographique système cohérente, avec vitesse à environ 112 px, rapport à 72 px, métriques principales à 30–36 px et texte secondaire à 18–22 px.
  - Ajouter un UiState QML qui normalise les données du bridge, les valeurs par défaut, unités, statuts et formats. Les nouveaux composants ne liront plus directement des dizaines de clés du bridge.
  - Remplacer les Repeaters de centaines de segments, fonds raster et effets de glow par quelques Shape, arcs et barres QML légers.
  - Constituer une petite bibliothèque commune : carte, métrique, bouton tactile, toggle, barre de progression, jauge, voyant, bannière, dialogue de confirmation et en-tête.
  - Ajouter un routeur central basé sur une liste de destinations. Une future destination média ou navigation pourra être enregistrée sans modifier les panneaux permanents, mais aucune destination Spotify/
    Waze ne sera créée dans cette refonte.

  ## Réorganisation des contenus

  - Conduite : profil actif CliOS, état du trajet, consommation instantanée et moyenne, Trip A/B, maintenance et représentation du véhicule uniquement lorsqu’une porte, le coffre ou la ceinture demande
    l’attention.

  - Trajet : conserver distance, carburant, coût, moyenne RPM, agressivité, roue libre et temps de passage. Les remises à zéro deviennent des actions explicites avec confirmation, sans appui long caché.
  - Performance : conserver accélérateur demandé/réel, embrayage, frein, couple, G longitudinal, patinage/blocage des quatre roues et bruit cabine. Le G-meter circulaire devient longitudinal puisque le
    backend ne fournit pas d’accélération latérale.

  - Diagnostic : états prêt/scan/OK/défauts, liste DTC et lancement du scan. L’effacement reste clairement désactivé tant qu’aucun slot backend réel ne l’implémente.
  - Menu : Apparence, Véhicule, Services, Système et Développeur. Le debug CAN quitte la navigation principale mais reste intégralement accessible.
  - Apparence : choix parmi les styles installés, aperçu immédiat et couleur d’accent discrète. La page Audio “en construction” disparaît du menu principal sans ajout de fonction média.
  - Système : informations CPU/RAM/CAN, stockage USB, services, logs, export diagnostic et commandes d’arrêt.
  - Session en pause : remplacer le déplacement complet des compteurs par une feuille centrale de résumé. Les panneaux latéraux restent stables.
  - Si une page complexe est ouverte au-dessus de 5 km/h, afficher pendant trois secondes une bannière ambre « Interaction complexe — restez attentif », sans empêcher la navigation.

  ## Validation

  - Vérifier au format exact 1920×720 les styles installés et chaque route, sans découpe, chevauchement ni texte tronqué.
  - Tester les états : démarrage/sweep, données absentes, faible carburant, surchauffe, redline, régulateur/limiteur, tous les voyants, portes/ceinture, USB normal/dégradé, services en erreur, trajet
    actif/pause/fin et conduite à plus de 5 km/h.

  - Tester les listes longues de profils, services, logs et DTC, ainsi que les formulaires et dialogues.
  - Vérifier la persistance du style et de l’accent après redémarrage et changement de profil.
  - Lancer qmllint, un chargement QML offscreen et des captures de référence 1920×720 pour chaque page et style.
  - Sur Raspberry Pi 5, vérifier la fluidité à 60 Hz, l’absence de pics liés aux anciennes jauges segmentées et une réaction visuelle en moins de 250 ms après un toucher.
  - Contrôler sur l’écran physique la lisibilité de jour à faible luminosité, la taille réelle des cibles et le contraste des textes secondaires.

  ## Hypothèses retenues

  - L’écran reste en orientation fixe 1920×720 et constitue une console centrale combinant instrumentation complémentaire et commandes.
  - L’utilisation est exclusivement tactile en voiture.
  - Toutes les fonctions restent accessibles en roulant ; seule une alerte de prudence est ajoutée.
  - Le style est enregistré par profil véhicule, comme la configuration visuelle actuelle.
  - Les anciens éléments graphiques restent confinés au paquet optionnel `legacy_dashboard` ; le style GT moderne ne les charge pas.
