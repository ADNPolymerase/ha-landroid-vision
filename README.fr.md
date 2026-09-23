<p align="center">
  <img src="https://raw.githubusercontent.com/ADNPolymerase/ha-landroid-vision/main/logo.png" alt="Worx Landroid Vision PLUS" width="380">
</p>

# Worx Landroid Vision PLUS

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://badgen.net/github/release/ADNPolymerase/ha-landroid-vision)](https://github.com/ADNPolymerase/ha-landroid-vision/releases)
[![Validate](https://github.com/ADNPolymerase/ha-landroid-vision/actions/workflows/validate.yml/badge.svg)](https://github.com/ADNPolymerase/ha-landroid-vision/actions/workflows/validate.yml)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2026.3%2B-blue.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/ADNPolymerase/ha-landroid-vision/blob/main/LICENSE)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow.svg?logo=buy-me-a-coffee)](https://buymeacoffee.com/adnpolymerase)

<a href="https://buymeacoffee.com/adnpolymerase" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-orange.png" alt="Buy Me A Coffee" height="60"></a>
<a href="https://adnpolymerase.github.io/HA/" target="_blank"><img src="https://raw.githubusercontent.com/ADNPolymerase/HA/main/assets/site-button.svg" alt="Lien vers mon github.io pour mes autres projets" height="60"></a>

Intégration Home Assistant personnalisée pour les tondeuses Worx Landroid Vision, Vision Cloud et RTK.

> 🇬🇧 [Read in English](README.md)

Elle s'appuie sur la bibliothèque communautaire `pyworxcloud` et ajoute une couche d'entités Home Assistant plus propre pour les tondeuses Vision : commandes de la tondeuse, capteurs utiles, diagnostics, calendrier du programme, rendu de la carte RTK et suivi quasi en direct de la position du robot.

## Fonctionnalités

- Entité `lawn_mower` native : démarrer, mettre en pause, rentrer à la base, tonte unique et coupe de bordure à la demande.
- Tonte unique par zone sur les tondeuses RTK, comme dans l'app Worx : choisissez les zones, un ordre imposé ou automatique et la routine de bordure, et la tondeuse les tond jusqu'au bout avant de rentrer. Disponible avec l'action `worx_vision_cloud.start_zone_mowing`, qu'une automatisation peut programmer, et avec le bouton Démarrer la tonte unique.
- Le motif de tonte (naturel, parallèle, losange, damier) et l'angle de chaque zone RTK, lus sur la tondeuse, avec une paire de capteurs par zone, nommée d'après elle. Affichage seulement : ces réglages se changent dans l'app Worx.
- Commandes de la tondeuse : mise à jour automatique du firmware, verrouillage, programme natif, coupe de bordure intelligente, protection des hérissons, mode festif et, si votre tondeuse signale le module matériel correspondant, ACS, zones interdites, hauteur de coupe, couple et distance de bordure.
- Suivi de la surface et de la progression du jour, enregistré par tondeuse dans Home Assistant, insensible aux remises à zéro des compteurs du cloud et aux trous de plusieurs jours, plus une estimation calculée localement qui continue d'avancer quand les statistiques de Worx ne bougent plus.
- Capteur et calendrier du programme (une semaine avant et après aujourd'hui par défaut, réglable dans les options de l'intégration), prochaine tonte, caméra de la carte RTK avec la trace de la surface tondue, position RTK du robot et adresse obtenue par géocodage inverse (à activer).
- Sur les tondeuses RTK, chaque créneau de la semaine indique les zones réglées dans l'app Worx, par leur nom, et si leur ordre est imposé. Elles apparaissent dans les événements du calendrier et dans l'attribut `slots` du capteur de programme (`zones`, `zone_names`, `zone_order`), prêtes pour une card ou un template.
- Capteurs de batterie, d'état, d'erreur, de connectivité, d'entretien et d'aptitude à tondre, avec des alertes dans Réparations pour l'entretien des lames et de la batterie et pour une tondeuse restée arrêtée loin de sa base, et un bouton de redémarrage.
- Téléchargement des diagnostics avec masquage automatique des coordonnées, des adresses et des identifiants.
- Traduite en 11 langues (anglais, polonais, français, allemand, néerlandais, espagnol, italien, suédois, norvégien, danois, russe), y compris les états des entités, le programme et le calendrier.

## Installation

### Option 1 : HACS (recommandé)

L'intégration est dans le magasin par défaut de HACS, aucun dépôt personnalisé n'est nécessaire :

1. Ouvrez HACS et cherchez `Worx Landroid Vision PLUS`.
2. Téléchargez-la.
3. Redémarrez Home Assistant.
4. Allez dans `Paramètres > Appareils et services > Ajouter une intégration` et cherchez `Worx Landroid Vision PLUS`.

### Option 2 : directement depuis ce dépôt

Sans HACS, copiez ce dossier :

```text
custom_components/worx_vision_cloud
```

dans le dossier de configuration de Home Assistant :

```text
/config/custom_components/worx_vision_cloud
```

Redémarrez ensuite Home Assistant et ajoutez l'intégration depuis `Paramètres > Appareils et services`. Avec cette méthode, les mises à jour sont à votre charge. Avec l'option 1, HACS s'en occupe.

À la configuration, connectez-vous avec l'adresse e-mail et le mot de passe de l'app de votre tondeuse, puis choisissez le cloud de votre marque : `worx`, `kress` ou `landxcape`.

## Entités

La liste exacte dépend de ce que votre tondeuse signale. On trouve en général :

- `lawn_mower` commande de la tondeuse
- `button` actualiser, remettre à zéro le temps des lames, remettre à zéro les cycles de batterie et lancer la coupe de bordure
- `calendar` programme de tonte
- `camera` carte RTK
- `device_tracker` position RTK du robot
- `sensor` batterie, état, erreur, aptitude, connexion au cloud, RSSI, programme, prochaine tonte, carte RTK, trace RTK, progression du jour, progression restante, surface tondue aujourd'hui et au total, surface et progression estimées du jour, temps de tonte du jour, surface de la pelouse, temps de fonctionnement, efficacité, fraîcheur des statistiques du cloud et valeurs d'entretien (le temps à la base et le temps de charge sont inclus mais désactivés par défaut, voir plus bas)
- `binary_sensor` en ligne, inscription IoT et MQTT, pluie, robot soulevé et mode pause
- `switch` mise à jour automatique du firmware, verrouillage, programme natif, coupe de bordure intelligente, protection des hérissons, mode festif, zones interdites et ACS (ces deux derniers seulement si votre tondeuse signale le module correspondant)
- `number` délai pluie, prolongation du programme, surface de la pelouse, périmètre de la pelouse, hauteur de coupe et couple (ces deux derniers seulement si votre tondeuse signale le module correspondant ; le couple est désactivé par défaut)
- `update` version du firmware, notes de version et installation OTA quand elle est prise en charge

Voir [docs/entities.md](docs/entities.md) pour une liste plus détaillée (en anglais).

## Card

L'intégration fournit sa propre card, **Worx Landroid Vision**, et l'enregistre pour vous : après une installation ou une mise à jour, rechargez le navigateur et choisissez-la dans la liste des cards. Elle affiche :

- l'état détaillé de la tondeuse (recherche d'une zone, traversée d'une bordure, départ de la base...) avec la zone où elle se trouve et la batterie, là où l'entité `lawn_mower` seule ne connaît que tonte, à la base, en pause, retour à la base ou erreur ;
- le signal Wi-Fi à côté de la batterie, l'aptitude à tondre, et un bandeau rouge avec l'erreur en cours et depuis quand, seulement quand il y en a une ;
- un bandeau bleu clair tant que la tondeuse attend à cause de la pluie, avec le temps restant avant qu'elle puisse ressortir et le délai pluie réglé, plutôt qu'une erreur en rouge ;
- démarrer, pause et retour à la base, et un bouton mode festif sous la batterie : tant qu'il est actif, un bandeau rappelle que la tondeuse ne sortira pas, même pendant le programme ;
- la carte RTK avec la trace du jour ;
- la tonte unique comme dans l'app Worx : cochez les zones, affichées côte à côte, gardez l'ordre dans lequel vous les avez cochées (Spécial) ou laissez la tondeuse choisir (Auto), ajoutez la coupe de bordure ou non, et démarrez ;
- le programme de la semaine reçu du cloud, replié sous le créneau en cours, ou sinon sous la prochaine tonte, et déplié jour par jour avec les zones, l'ordre et la coupe de bordure de chaque créneau ;
- le temps actuel des lames, comme dans l'app Worx, avec la progression vers le seuil d'entretien, et un bouton de remise à zéro qui demande d'abord confirmation.

Un clic sur l'état, la zone, la batterie, le Wi-Fi, l'aptitude, l'erreur, le bandeau pluie ou la carte ouvre la fenêtre de détail de Home Assistant, avec son historique.

```yaml
type: custom:worx-vision-card
entity: lawn_mower.votre_tondeuse
```

Seul `entity` est nécessaire : la card trouve d'elle-même les autres entités de la même tondeuse, les renommer ne la casse donc pas. En option : `title`, `show_info`, `show_controls`, `show_map`, `show_zones`, `show_schedule`, `show_blades` (tous à `true` par défaut) et `refresh_interval` pour la carte, en secondes (30 par défaut, 0 pour ne jamais la rafraîchir). Sur une Landroid plus ancienne, sans carte RTK ni zones, la card affiche l'état, les commandes et le programme.

La card se trouve dans ce dépôt, dans `custom_components/worx_vision_cloud/worx-vision-card.js`.

Elle remplace `worx-map-rtk-card.js`, qui n'est plus dans ce dépôt. Une ressource Lovelace qui pointe encore dessus est retirée automatiquement, et les tableaux de bord qui utilisent toujours `custom:worx-map-rtk-card` continuent d'afficher la carte, désormais dessinée par la nouvelle card.

*Si vos ressources Lovelace sont gérées en YAML, l'intégration n'y écrit jamais : ajoutez vous-même `/worx_vision_cloud_frontend/worx-vision-card.js` comme ressource de type `module`.*

La **[landroid-card](https://github.com/Barma-lej/landroid-card)** de Barma-lej fonctionne aussi avec ces entités, si vous préférez une card commune à plusieurs marques de tondeuses et d'aspirateurs. Faites pointer son option `camera:` sur la caméra de la carte RTK pour y afficher la carte.

L'entité `lawn_mower` n'a volontairement pas de nom propre : elle affiche exactement le nom de l'appareil, et elle reste disponible pendant les coupures de connexion au lieu de passer indisponible. Les deux servent les cards comme la landroid-card, qui s'en servent comme préfixe du nom de toutes les autres entités et vident leur contenu quand elle est indisponible. Seules les commandes sont bloquées quand la tondeuse est réellement hors ligne, avec un message d'erreur clair.

## Carte RTK et adresse

Pour les tondeuses Vision Cloud et RTK, une entité caméra dessine en SVG, à partir du point d'accès privé des cartes Worx, la limite du terrain, les zones exclues, la station, la trace de tonte du jour et le robot tourné dans sa direction de marche. Ce n'est pas un flux vidéo : l'image se met à jour à l'arrivée de nouvelles données. La trace couvre toute la journée locale comme dans l'app Worx, repart à zéro à minuit, survit à un redémarrage, et la dernière carte connue est gardée si un téléchargement échoue brièvement.

Un capteur `Adresse RTK` (désactivé par défaut) obtient l'adresse de la position arrondie de la tondeuse par géocodage inverse avec OpenStreetMap Nominatim, avec un cache de 24 h. Il faut l'activer vous-même, car les coordonnées RTK peuvent révéler l'emplacement d'un domicile. Les cartes et les coordonnées sont précises : ne publiez pas de journaux de débogage, de fichiers de stockage, de jetons ni de captures d'écran qui les montrent. Voir [SECURITY.md](SECURITY.md).

### Récupérer la carte après une mise à jour depuis une ancienne version

*Avant la 1.6.3, l'identifiant de la carte RTK n'était pas mis en cache : la caméra de la carte et les capteurs de surface et de progression pouvaient se vider dès que Worx cessait de l'envoyer. Il est depuis mis en cache et conservé, mais ce cache est vide au premier redémarrage après la mise à jour. Si ces entités sont alors indisponibles, ouvrez l'historique du capteur **Carte RTK**, prenez le dernier UUID qu'il a affiché, et passez-le à l'action `worx_vision_cloud.set_rtk_map_id` avec votre entité `lawn_mower`. Tout se met à jour aussitôt, puis reste à jour tout seul.*

## Surface tondue

Les chiffres de tonte sont une surface parcourue, pas une surface de pelouse unique : avec les passages qui se chevauchent, Surface tondue aujourd'hui et Surface totale tondue peuvent dépasser la taille de votre pelouse, et Progression quotidienne atteint 100 % dès que la surface parcourue l'égale. La référence du jour est enregistrée par tondeuse : elle survit aux redémarrages et aux renommages d'entités, et gère les remises à zéro des compteurs du cloud et les trous de plusieurs jours.

La surface de la pelouse vient du `lawn_size` du compte quand Worx en fournit un, sinon de la somme des zones tondues de la carte RTK. Les zones que la tondeuse ne fait que traverser, comme un couloir entre deux zones de tonte, n'ont pas de réglages de coupe et sont exclues : le chiffre correspond ainsi à celui de l'app Worx plutôt qu'au total brut de la carte.

### Une réserve sur le rattachement au jour

Surface tondue aujourd'hui et Progression quotidienne viennent du compteur cumulé du cloud : elles suivent le moment où Worx **publie** une session, pas celui où la tondeuse a réellement tondu. La publication peut avoir des heures de retard : une session observée a duré de 14:02 à 17:54, et ses 310 m² ne sont apparus qu'à 03:26 le lendemain matin, comptés pour le jour suivant.

Rien n'est perdu, Surface totale tondue reste juste. Pour un chiffre qui suit la journée en cours au fil de l'eau, utilisez les capteurs calculés localement, Surface estimée tondue aujourd'hui et Progression quotidienne estimée, tirés du temps de tonte observé plutôt que du compteur du cloud.

## Limites

L'API cloud de Worx / Positec n'est pas publique officiellement. Certains points d'accès utilisés ici ont été retrouvés par rétro-ingénierie et peuvent changer sans prévenir. C'est une intégration personnalisée faite au mieux, pas un logiciel officiel Worx.

- Les entités zones interdites et ACS peuvent afficher `unavailable` sur une tondeuse qui les prend en charge. Leur disponibilité dépend de ce que pyworxcloud voie le module correspondant (`DF`, `US`) dans les données en direct, et le module des zones interdites n'apparaît qu'une fois une zone configurée au moins une fois dans l'app Worx. C'est une limite des données de l'API, commune avec l'intégration communautaire `landroid_cloud`.
- Worx ne publie les notes de version du firmware que tant qu'une mise à jour est en attente ; une fois installée, le point d'accès répond 404 et elles disparaissent. L'intégration les enregistre au passage, mais rien ne peut être récupéré pour une version installée avant. Utilisez l'action `worx_vision_cloud.set_firmware_notes` pour les recopier depuis le portail du compte Worx.
- Une mise à jour qui ne concerne que la tête Vision est invisible ici. Le firmware est livré par paire tête et tondeuse, mais la disponibilité se calcule en comparant les seules versions de la tondeuse, et la version de la tête n'est pas exposée du tout. Les deux viennent de l'API ; l'app Worx reste la référence pour le firmware de la tête.
- Sur une tondeuse Vision, la tonte unique ne prend pas de durée, comme dans l'app Worx : la tondeuse tond les zones choisies jusqu'au bout. Démarrer reprend tout ce qui reste à tondre, toutes les zones inachevées comprises, comme le bouton lecture de l'app : utilisez la tonte unique pour l'envoyer sur des zones précises. Une commande envoyée pendant que la tondeuse ne parle pas au cloud est perdue, pas mise en attente : une tonte de zone dont la tondeuse n'accuse pas réception est vérifiée dans son rapport suivant et renvoyée une seule fois si elle n'a pas démarré, et une alerte dans Réparations le signale si le deuxième envoi ne démarre pas non plus.
- Le temps à la base et le temps de charge peuvent rester à `0` pour certains comptes, car l'API ne les renseigne pas pour tous les modèles. Les deux capteurs sont désactivés par défaut ; activez-les si votre compte remonte de vraies valeurs.

## Remerciements

- Utilise [`pyworxcloud`](https://github.com/MTrab/pyworxcloud).
- Intégration préparée à l'origine par Smart Service.
