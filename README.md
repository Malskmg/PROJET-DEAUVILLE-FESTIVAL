# Festival OS — Deauville Festival du Rire

Application de gestion du programme du Deauville Festival du Rire 2027.

Le projet comprend :

- un modèle métier Python ;
- un stockage JSON ;
- une interface en ligne de commande ;
- une API FastAPI ;
- une interface Streamlit avec CSS indépendant ;
- des tests automatisés.

## 1. Prérequis

- Python 3.12, ou installation de cette version par uv ;
- uv ;
- Git pour cloner le projet.

Les commandes suivantes sont exécutées depuis la racine du projet.

## 2. Installation

Après clonage du dépôt :

```powershell
uv sync --locked
```

Le fichier `uv.lock` est conservé dans le dépôt.

Le jeu de données initial est situé dans :

```text
data/festival.json
```

## 3. Ligne de commande

Résumé :

```powershell
uv run main.py
```

Programme d'une journée :

```powershell
uv run main.py programme --day 2027-06-11
```

Programme d'un lieu :

```powershell
uv run main.py programme --day 2027-06-11 --venue le-kiosque
```

Artistes et nombre de représentations :

```powershell
uv run main.py artists
```

Spectacles en cours et trois suivants :

```powershell
uv run main.py now --at 2027-06-11T21:00
```

Utiliser un autre fichier :

```powershell
uv run main.py --data data/festival.demo.json summary
```

Sans `--at`, la CLI utilise l'heure locale de l'ordinateur.

## 4. Démarrer l'API

Dans un premier terminal :

```powershell
uv run uvicorn festival.api.app:app --app-dir src --reload
```

Adresses :

- documentation : http://127.0.0.1:8000/docs
- API : http://127.0.0.1:8000/api/festival
- site HTML public : http://127.0.0.1:8000/
- administration HTML : http://127.0.0.1:8000/admin/

Les interfaces HTML nécessitent leurs fichiers et ressources dans :

```text
web/public/
web/admin/
```

Si un dossier ne contient pas son `index.html`, une page informative est affichée à la place.

Les ressources HTML réellement présentes dans le dépôt doivent être vérifiées avant la remise.

## 5. Démarrer Streamlit

Dans un deuxième terminal :

```powershell
uv run streamlit run streamlit_app/app.py
```

Adresse :

```text
http://localhost:8501
```

Le backend doit rester démarré.

Pour changer l'adresse de l'API :

```powershell
$env:FESTIVAL_API_URL = "http://127.0.0.1:8000"
uv run streamlit run streamlit_app/app.py
```

Ne pas ajouter `/api` à cette variable.

## 6. Données de démonstration

Créer une copie sans écraser une copie existante non vérifiée :

```powershell
Copy-Item data/festival.json data/festival.demo.json
```

Démarrer le backend de démonstration à la place du backend principal :

```powershell
uv run uvicorn --app-dir src --factory "festival.api.demo:create_demo_app" --reload
```

Les modifications effectuées dans Streamlit ou dans `/docs` sont réelles.
Elles concernent le fichier utilisé par le backend.

## 7. Architecture

```text
src/festival/
├── domain/
│   ├── entities.py
│   ├── performances.py
│   ├── festival.py
│   ├── identifiers.py
│   └── errors.py
├── application/
│   ├── ports.py
│   └── services.py
├── infrastructure/
│   ├── serialization.py
│   └── json_repository.py
├── api/
│   ├── app.py
│   ├── routes.py
│   ├── schemas.py
│   └── presenters.py
└── cli/
    └── commands.py

streamlit_app/
├── app.py
├── api_client.py
├── components.py
├── views/
└── assets/styles.css
```

### Modèle métier

`Artist` et `Venue` représentent les références du festival.

`Performance` est une classe abstraite qui définit les propriétés communes :
titre, lieu, début, durée, fin, identifiant et journée du festival.

`Solo`, `Lineup` et `Workshop` implémentent leurs contraintes spécifiques.

Les objets métier élémentaires sont non modifiables directement.
Les changements de spectacle produisent de nouvelles versions.

`Festival` contrôle les références, les journées autorisées, les doublons et les conflits.
Ses collections sont exposées sous forme de tuples.

L'encapsulation protège l'utilisation normale de l'interface publique.
Elle n'est pas une protection contre un programme qui modifierait volontairement les attributs internes Python.

### Services et sauvegarde

`FestivalService` applique les modifications à une copie du festival.

Il sauvegarde cette copie avant de publier le nouvel état.
Un échec de validation ou de sauvegarde laisse son état précédent inchangé.

Les opérations de modification de l'application passent par ce service.

`JsonFestivalRepository` reconstruit le modèle au chargement et réapplique les validations.

La sauvegarde écrit un fichier temporaire voisin avant remplacement du fichier cible.

### Séparation des interfaces

Streamlit communique avec FastAPI par HTTP.

FastAPI traduit les requêtes et les erreurs.
Les règles de planning restent dans le domaine.

La CLI utilise le même modèle, chargé par le service.

### Évolution vers SQLite

Une nouvelle implémentation de `FestivalRepository` pourrait remplacer le dépôt JSON.

Le modèle métier resterait inchangé.
La configuration de l'application devrait sélectionner le nouveau dépôt.

Le module de présentation HTTP réutilise actuellement une fonction de sérialisation du module infrastructure.
Cette dépendance légère pourrait être extraite dans un module de conversion partagé lors d'une évolution.

## 8. Principales règles

- Noms nettoyés et non vides.
- Slugs ASCII pour les artistes et les lieux.
- Durée comprise entre 1 et 360 minutes.
- Journée de festival avec bascule à 06 h.
- Pause minimale de 30 minutes pour un lieu.
- Pause minimale de 30 minutes pour un artiste, tous rôles confondus.
- Validation des plateaux.
- Capacité des ateliers limitée par le lieu et le maximum prévu.
- Inscriptions sans doublons, sans distinction de casse.
- Modification refusée sans altération de l'état initial.

## 9. Erreurs HTTP

- 404 : ressource inconnue.
- 409 : conflit métier.
- 422 : valeur ou requête invalide.
- 500 : échec de lecture ou de sauvegarde.

Les erreurs métier donnent un `detail` textuel.
Les erreurs de validation de requête FastAPI donnent un `detail` sous forme de liste.

Le contrat détaillé est dans `API.md`.

## 10. Tests et qualité

Tous les tests :

```powershell
uv run pytest -q
```

Formatage :

```powershell
uv run ruff format src streamlit_app tests main.py
```

Vérification Ruff :

```powershell
uv run ruff check src streamlit_app tests main.py
```

Construction :

```powershell
uv build
```

Vérification générale sous Windows :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

Les tests d'écriture utilisent des copies temporaires des données.

Certains tests d'intégration vérifient les effectifs du jeu de données initial.
Il faut donc conserver le fichier initial et utiliser une copie pour les démonstrations.

Les tests Streamlit utilisent AppTest.
Ils vérifient notamment le chargement des pages, la navigation, la recherche et l'affichage d'une erreur API.
Ils ne valident pas le rendu exact du CSS dans un navigateur.

## 11. Construction et distribution

Le wheel contient le paquet Python `festival`.

L'archive source inclut les ressources du projet sélectionnées dans `pyproject.toml`.

Le mode d'exécution documenté reste celui du projet cloné.
Le wheel seul n'est pas une installation autonome de toutes les interfaces et données.

## 12. Fonctionnalités réalisées

- Artistes et lieux.
- Solos, plateaux et ateliers.
- Validation du planning.
- Chargement et sauvegarde JSON.
- CLI.
- Routes HTTP du contrat.
- Interface Streamlit connectée.
- Programmation, modification et annulation.
- Ajout d'artistes.
- Inscription aux ateliers.
- Tests automatisés.

## 13. Limites connues

- Pas d'authentification ni de gestion des rôles.
- Pas de dépôt SQLite.
- Pas de billetterie ni de paiement.
- Pas de verrouillage partagé entre plusieurs processus.
- Pas de surveillance des modifications externes du JSON pendant l'exécution.
- Pas de mise à jour permanente en arrière-plan de Streamlit.
- Pas de garantie de résistance à toutes les formes de panne matérielle.
- Pas de validation visuelle automatisée complète des interfaces HTML.
- Les photos ne sont pas affichées dans la fiche artiste Streamlit.
- Les participants aux ateliers sont présents dans les réponses prévues par le contrat :
  une publication réelle demanderait une revue des accès et de la confidentialité.

L'application doit rester locale dans cette version.
Elle ne doit pas être exposée publiquement sans protections supplémentaires.

## 14. Arrêter les serveurs

Dans chacun des terminaux concernés :

```text
Ctrl + C
```