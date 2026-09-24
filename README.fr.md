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


Intégration Home Assistant pour les tondeuses Worx Landroid Vision, Vision Cloud et RTK, construite sur [`pyworxcloud`](https://github.com/MTrab/pyworxcloud), avec sa propre card de tableau de bord.

> 🇬🇧 [Read in English](README.md)

## Fonctionnalités

- Entité `lawn_mower` : démarrer, pause, retour à la base, tonte unique et coupe de bordure.
- Tonte unique par zone comme dans l'app Worx : zones, ordre imposé ou automatique, routine de bordure. Aussi avec l'action `worx_vision_cloud.start_zone_mowing`, pour les automatisations.
- Le motif et l'angle de tonte de chaque zone RTK, en lecture seule.
- Réglages de la tondeuse : verrouillage, programme, coupe de bordure intelligente, protection des hérissons, mode festif, délai pluie, et hauteur de coupe, couple, zones interdites ou ACS quand la tondeuse les a.
- Surface tondue et progression du jour conservées par l'intégration, plus une estimation locale qui avance quand les statistiques Worx sont en retard.
- Capteur et calendrier du programme avec les zones de chaque créneau, caméra de la carte RTK avec la trace du jour, position du robot.
- Capteurs d'état, d'erreur, d'aptitude, de batterie et d'entretien, avec des alertes dans Réparations pour l'entretien des lames et de la batterie et pour une tondeuse arrêtée loin de sa base.
- Diagnostics avec coordonnées et identifiants masqués. 11 langues.

La liste complète des entités est dans [docs/entities.md](docs/entities.md) (en anglais).

## Installation

Dans HACS, cherchez `Worx Landroid Vision PLUS`, téléchargez-la, redémarrez Home Assistant, puis ajoutez l'intégration dans `Paramètres > Appareils et services`. Connectez-vous avec l'e-mail et le mot de passe de l'app de votre tondeuse, et choisissez le cloud de votre marque : `worx`, `kress` ou `landxcape`.

Sans HACS, copiez `custom_components/worx_vision_cloud` dans `/config/custom_components/` et redémarrez.

## Card

L'intégration fournit la card **Worx Landroid Vision** et l'enregistre elle-même : rechargez le navigateur et choisissez-la dans la liste des cards.

```yaml
type: custom:worx-vision-card
entity: lawn_mower.votre_tondeuse
```

Elle affiche l'état détaillé (recherche d'une zone, traversée d'une bordure...), la batterie et le Wi-Fi, les bandeaux d'erreur et de pluie, le mode festif, démarrer, pause et retour à la base, la carte RTK avec, juste dessous, une fine barre de la progression estimée du jour, la tonte unique par zone, le programme de la semaine et le temps des lames avec sa remise à zéro. La tonte unique reste repliée sur une ligne, avec le résumé de ses réglages et Démarrer à droite ; dépliez-la pour choisir les zones, l'ordre et la coupe de bordure. Les derniers réglages sont mémorisés dans le navigateur. Un clic sur une valeur ouvre son historique. Seul `entity` est nécessaire : la card trouve le reste de la tondeuse toute seule. En option : `title`, `show_info`, `show_controls`, `show_map`, `show_zones`, `show_schedule`, `show_blades`, `show_values` (pourcentage de batterie et dBm du Wi-Fi à côté de leurs icônes) et `refresh_interval` (carte, en secondes). La batterie et le Wi-Fi passent au vert, à l'orange ou au rouge selon leur niveau. Sur une Landroid plus ancienne, elle affiche l'état, les commandes et le programme.

*Avec des ressources Lovelace en YAML, ajoutez vous-même `/worx_vision_cloud_frontend/worx-vision-card.js` comme ressource `module`.*

La [landroid-card](https://github.com/Barma-lej/landroid-card) de Barma-lej fonctionne aussi avec ces entités.

## Bon à savoir

- La carte RTK et les coordonnées sont précises : ne publiez pas de journaux ni de captures d'écran qui les montrent. Le capteur d'adresse est désactivé par défaut. Voir [SECURITY.md](SECURITY.md).
- La surface tondue est une surface parcourue : avec les passages qui se chevauchent, elle peut dépasser celle de la pelouse. Le cloud publie une session en retard, parfois le lendemain : les capteurs estimés suivent la journée en cours.
- Sur une Vision, la tonte unique ne prend pas de durée. Démarrer reprend toutes les zones inachevées, comme le bouton lecture de l'app. Une commande envoyée pendant que la tondeuse dort est perdue : une tonte de zone est vérifiée puis renvoyée une fois, et une alerte dans Réparations le signale si elle ne démarre toujours pas.
- L'API cloud de Worx n'est pas publique et peut changer sans prévenir. Ce n'est pas un logiciel officiel Worx.

## Remerciements

Utilise [`pyworxcloud`](https://github.com/MTrab/pyworxcloud). Préparée à l'origine par Smart Service.
