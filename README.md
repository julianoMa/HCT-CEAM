# HCT-CEAM

Plateforme interne de gestion des rapports d'incidents pour la **Commission d'Éthique des Affaires Médicales (CEAM)** du serveur de roleplay HCT. Permet au personnel des établissements TMC et NMH de déposer des rapports, à la commission de les instruire, et à tout le monde de suivre l'avancement en temps réel — sur le site et sur Discord.

## Fonctionnalités

### Authentification
- Connexion via Discord OAuth2, avec vérification de l'appartenance au serveur HCT
- Récupération du pseudo du serveur (pas le nom Discord global) et de l'avatar
- Session longue durée (30 jours)

### Espace personnel (déclarant)
- **Dépôt d'un rapport** : formulaire en 5 sections (Plaignant, Mis en cause, Circonstances de l'incident, Exposé des faits, Témoins), case de certification sur l'honneur obligatoire
- **Preuves** : liens et fichiers (PDF/images) ajoutés via un modal dédié, avec compression automatique des images côté navigateur avant l'envoi
- **Mes dossiers** : suivi de ses propres rapports, plus ceux où l'on a été ajouté comme tiers par la commission
- **Notifications** : in-app (cloche + historique + marquage lu/non lu) et par MP Discord (embeds), à chaque étape clé (rapport envoyé, changement de statut, nouvelle réponse, ajout en tant que tiers)
- **Export PDF** d'un dossier individuel (infos, historique, réponses)
- **Règlement CEAM** et **page d'accueil** pédagogique, consultables par tous

### Espace commission (CEAM)
- **Suivi CEAM** : tous les dossiers non archivés, avec recherche (référence/nom), filtre par statut, et pagination
- **Suivi interne** (statut + note privée) séparé des **réponses officielles** envoyées au déclarant (accusé de réception automatique, puis réponses libres avec pièces jointes)
- **Historique des statuts** horodaté
- **Gestion des tiers** : donner l'accès à un dossier à une personne supplémentaire (témoin, etc.), qui reçoit alors les mêmes notifications que le déclarant
- **Archivage** (président) et **suppression définitive** (admin), avec confirmation
- **Statistiques** : délai moyen de traitement, répartition TMC/NMH, alerte de relance sur les dossiers stagnants
- **Prévisualisation des pièces jointes** dans un modal (image ou PDF affiché directement, bouton de téléchargement séparé)

### Administration
- Gestion des utilisateurs et des rôles
- **Journal d'activité** : toutes les actions sensibles (rôles, dépôts, statuts, réponses, tiers, règlement), avec recherche par auteur/détails, filtre par type d'action, et pagination

### Interface
- Mode sombre / clair (persisté, sans flash au chargement)
- Rendu enrichi des liens (images, YouTube) dans les descriptions et réponses

## Rôles

| Rôle | Valeur | Peut |
|---|---|---|
| Déclarant | 0 | Déposer des rapports, suivre les siens |
| Membre CEAM | 1 | Instruire les dossiers, répondre, gérer les tiers |
| Président CEAM | 2 | + Archiver un dossier |
| Administrateur | 3 | + Supprimer un dossier, gérer les rôles, voir le journal d'activité |

## Stack technique

- **Backend** : Flask, Flask-Login, Flask-WTF
- **Base de données** : Firestore (Firebase) — y compris le stockage des pièces jointes en base64 (pas de Firebase Storage, qui nécessite un plan payant)
- **Authentification** : Discord OAuth2
- **Notifications** : bot Discord (MP en embeds) + notifications in-app
- **Export PDF** : fpdf2 (pur Python, sans dépendance système — compatible hébergement serverless)
- **Déploiement** : Vercel

## Structure du projet

```
app/
├── __init__.py              # Factory Flask, context processor (compteur de notifications)
├── config.py                 # Configuration (variables d'environnement)
├── extensions.py             # Initialisation Firestore
├── permissions.py            # Décorateur requires_role
├── rich_text.py               # Filtre Jinja pour liens/images/YouTube
├── notifications.py          # Envoi de MP Discord (embeds)
├── startup_check.py          # Vérification des variables d'env + connexion Firestore au démarrage
├── storage.py                 # Stockage des pièces jointes (base64 dans Firestore)
├── pdf_export.py               # Génération du PDF d'un dossier
├── models/
│   ├── ceam.py                # Modèle Rapport (dossiers)
│   ├── user.py                 # Modèle User
│   ├── notification.py         # Modèle Notification (in-app)
│   ├── audit_log.py            # Journal d'activité
│   └── reglement.py            # Règlement CEAM (contenu éditable)
├── auth/                       # Routes et logique Discord OAuth2
├── ceam/                       # Routes et formulaires métier (dépôt, suivi, détail, notifications...)
├── admin/                      # Routes d'administration (utilisateurs, journal)
├── templates/                  # Templates Jinja (base, ceam/, auth/, admin/, macros/)
└── static/
    ├── css/style.css
    └── js/app.js

pyproject.toml                  # Dépendances + config Vercel (entrypoint: run:app)
run.py                          # Point d'entrée WSGI
```

## Installation locale

```bash
git clone https://github.com/julianoMa/HCT-CEAM.git
cd HCT-CEAM
pip install -r requirements.txt
```

Créer un fichier `.env` à la racine avec au minimum :

```env
SECRET_KEY=
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
DISCORD_REDIRECT_URI=http://localhost:5000/auth/callback
DISCORD_GUILD_ID=
DISCORD_BOT_TOKEN=
FIREBASE_CREDENTIALS_JSON=
STARTUP_HEALTHCHECK=1
```

- `FIREBASE_CREDENTIALS_JSON` : le contenu JSON complet de la clé de service Firebase, sur une seule ligne
- `DISCORD_BOT_TOKEN` : nécessaire pour les MP Discord (notifications) — le bot doit être invité sur le serveur HCT
- `STARTUP_HEALTHCHECK=0` pour désactiver la vérification au démarrage

Lancer en local :

```bash
flask run
```

## Déploiement (Vercel)

Le déploiement utilise `pyproject.toml` (pas `requirements.txt`) :

```toml
[tool.vercel]
entrypoint = "run:app"
```

Toutes les variables d'environnement ci-dessus doivent être configurées dans les paramètres du projet Vercel.

## Modèle de données (Firestore)

| Collection | Contenu |
|---|---|
| `ceam` | Les dossiers (rapports), avec réponses, historique de statuts, tiers, pièces jointes en base64 |
| `utilisateurs` | Profils (nom, rôle, avatar, Discord ID) |
| `notifications` | Notifications in-app par utilisateur |
| `logs` | Journal d'activité |
| `config` | Contenu du règlement CEAM |
| `attachments` | Données brutes des pièces jointes (base64) |
| `counters` | Compteurs pour les identifiants incrémentaux |

## Points d'attention

- **Index composites Firestore** : certaines requêtes (recherche combinée à un tri, ou `array_contains` avec égalité) demandent la création d'un index composite. Si une erreur `FailedPrecondition` apparaît en console, cliquer sur le lien fourni pour créer l'index — l'opération prend quelques minutes.
- **Limite des pièces jointes** : 650 Ko par fichier (contrainte du plan Firestore gratuit, encodage base64 inclus). Les images sont automatiquement compressées côté navigateur avant l'envoi ; les PDF ne le sont pas.
- **Fuseau horaire** : toutes les dates sont actuellement stockées et affichées en UTC, sans conversion.