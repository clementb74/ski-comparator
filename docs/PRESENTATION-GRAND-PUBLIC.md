# Le comparateur de stations de ski — expliqué simplement

## En une phrase

Un site qui aide à choisir où skier en France en comparant automatiquement
l'enneigement, la météo et le risque d'avalanche de 20 stations des Alpes,
et qui affiche tout ça sur une carte.

## Le problème que ça résout

Quand on veut partir au ski, on doit aujourd'hui consulter plusieurs sites
différents : un pour la météo, un autre pour le bulletin neige, un autre
pour le risque d'avalanche, encore un autre pour savoir quelles pistes sont
ouvertes. C'est long, et il n'existe pas d'endroit unique qui compare
plusieurs stations entre elles avec ces critères.

Ce projet rassemble automatiquement toutes ces informations au même
endroit, calcule une note globale par station ("score de qualité neige"),
et permet de comparer plusieurs stations côte à côte sur une carte.

## Comment ça marche, en langage simple

Imaginez trois étapes, comme dans une cuisine de restaurant :

1. **Les courses** (la collecte des données) — Des petits programmes vont
   automatiquement chercher les informations sur différents sites internet
   officiels : la hauteur de neige, le risque d'avalanche, l'altitude et la
   position de chaque station. C'est comme envoyer quelqu'un faire les
   courses tous les jours plutôt que de tout acheter à la main.

2. **La préparation** (le rangement et le nettoyage des données) — Ces
   informations brutes, souvent en vrac et dans des formats différents,
   sont nettoyées, triées et rangées dans une grande base de données bien
   organisée. C'est l'équivalent d'une cuisine où chaque ingrédient a sa
   place précise, pour qu'on puisse cuisiner vite et sans erreur.

3. **Le service** (le site web) — Une fois les données prêtes, un site web
   avec une carte interactive les affiche : chaque station apparaît comme
   un point coloré (vert si les conditions sont bonnes, rouge si elles sont
   moins bonnes, gris si on n'a pas encore l'information). On peut cliquer
   sur une station pour voir sa fiche, ou en sélectionner plusieurs pour
   les comparer dans un tableau.

## Ce que fait la note ("score de qualité neige")

Chaque station reçoit une note sur 100, calculée à partir de trois
éléments :
- la **quantité de neige** actuelle (la moitié de la note),
- la **fraîcheur** de la dernière chute de neige (un quart de la note) —
  mieux vaut de la neige tombée hier que la semaine dernière,
- le **nombre de pistes ouvertes** (le dernier quart).

Le **risque d'avalanche** est affiché à côté, mais n'entre pas dans le
calcul de la note : ce n'est pas un critère de "qualité" mais une
information de sécurité, qu'il vaut mieux montrer séparément plutôt que de
la mélanger avec le reste.

Si une station n'a pas encore communiqué d'information (par exemple hors
saison, l'été), la note affiche "pas de donnée" plutôt qu'une fausse note —
c'est plus honnête que d'inventer un chiffre.

## Pourquoi ce projet, et ce qu'il démontre

Ce n'est pas qu'un site web : c'est surtout un projet qui montre toute la
chaîne derrière un produit de données, de la collecte brute jusqu'à
l'affichage pour l'utilisateur final — un parcours complet qu'on retrouve
dans beaucoup de métiers techniques aujourd'hui (data engineer, data
analyst, développeur full-stack).

Il a aussi fallu résoudre de vrais problèmes concrets en cours de route :
des sites qui bloquent trop de visites rapprochées, des informations qui ne
sont disponibles qu'en hiver, des noms de lieux qui ne correspondent pas
exactement d'une source à l'autre... Ce sont typiquement les difficultés
auxquelles on fait face en vrai, pas dans un exercice simplifié.

## Les limites actuelles, honnêtement

- Le projet a été construit hors saison (en automne), donc beaucoup de
  stations affichent "pas de donnée" pour l'instant — tout est prêt pour
  se remplir automatiquement dès la réouverture des stations en novembre.
- Seules 20 stations des Alpes du Nord sont suivies pour l'instant (c'est
  volontaire, pour garder un périmètre gérable) — en ajouter d'autres ne
  demande qu'une ligne dans un fichier de configuration.
- Les critères "niveau de ski" et "budget" ne sont pas encore pris en
  compte, faute d'avoir trouvé une source de données fiable pour ça.
