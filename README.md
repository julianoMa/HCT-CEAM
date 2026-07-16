# CEAM — Commission d'Éthique des Affaires Médicales

Application Flask pour la gestion des rapports d'incidents et de plaintes
entre membres du personnel HCT (TMC / NMH), avec connexion Discord et
stockage sur **Firebase Firestore**.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate        # ou venv\Scripts\activate sous Windows
pip install -r requirements.txt
```

Copie `.env.example` en `.env` et remplis les valeurs :

```bash
cp .env.example .env
```

### Configurer Firebase

1. Dans la [Console Firebase](https://console.firebase.google.com/), crée
   un projet (ou utilise l'existant) et active **Firestore Database**.
2. Paramètres du projet > Comptes de service > "Générer une nouvelle clé
   privée" → télécharge le fichier JSON.
3. Place ce fichier à la racine du projet (ex: `firebase-credentials.json`)
   et renseigne son chemin dans `FIREBASE_CREDENTIALS_PATH`.
4. **Ne commite jamais ce fichier** (ajoute-le à `.gitignore`) : il donne un
   accès complet à ta base Firestore.

### Configurer Discord

- `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` : créés depuis le
  [Discord Developer Portal](https://discord.com/developers/applications),
  onglet OAuth2.
- `DISCORD_REDIRECT_URI` : doit être ajoutée dans "Redirects" côté Discord,
  exactement identique (ex: `http://localhost:5000/auth/callback`).
- `DISCORD_GUILD_ID` : identifiant du serveur Discord HCT, pour vérifier
  que la personne est toujours membre (mode développeur Discord activé,
  clic droit sur le serveur > Copier l'identifiant).

## Lancer le site

```bash
flask run
```

Le site est accessible sur http://localhost:5000. Le premier utilisateur
qui se connecte via Discord est créé automatiquement dans la collection
Firestore `utilisateurs`, avec le rôle `Déclarant` (0). Pour lui donner un
rôle supérieur au tout début (aucun administrateur n'existe tant que
personne n'a le rôle 3), modifie-le directement dans la Console Firebase :
Firestore Database > collection `utilisateurs` > document correspondant >
champ `role` → mets `3`.

## Structure du projet

- `app/models/` — `User` et `Rapport`, classes Python qui encapsulent les
  accès aux collections Firestore `utilisateurs` et `ceam`, fidèles au
  schéma de données fourni.
- `app/firestore_utils.py` — génère des identifiants entiers auto-
  incrémentés (`id` int64) via un compteur Firestore transactionnel,
  puisque Firestore n'a pas d'auto-incrément natif comme une base SQL.
- `app/auth/` — connexion OAuth2 Discord (login, callback, logout).
- `app/ceam/` — dépôt de rapport, mes dossiers, suivi, archives,
  statistiques, détail d'un dossier.
- `app/admin/` — gestion des rôles des utilisateurs.
- `app/permissions.py` — décorateur `@requires_role(niveau)` pour
  protéger les routes selon le rôle (0 à 3).
- `app/templates/` — gabarits Jinja2, style "institutionnel sobre"
  (blanc / gris / bleu marine).

## Organisation des données dans Firestore

```
utilisateurs/{id}          → discord_id, name, role
ceam/{id}                  → plaignant_*, concerne_*, event_date, event_hour,
                              witness, description, proof, send_date,
                              owner_id, status, note, conclusion
counters/{utilisateurs|ceam} → value (compteur interne, ne pas modifier)
```

Les champs `event_date`, `event_hour` et `send_date` sont stockés comme
des **chaînes** (conformément au schéma fourni), au format ISO
(`YYYY-MM-DD`, `HH:MM`, `YYYY-MM-DDTHH:MM`) pour rester triables. Les
templates les affichent au format français via les propriétés
`event_date_fr` / `send_date_fr`.

## Rôles (rappel)

| Valeur | Rôle             | Peut faire |
|--------|------------------|------------|
| 0      | Déclarant        | Déposer un rapport, voir ses dossiers |
| 1      | Membre CEAM      | + Suivi, notes internes, changer le statut |
| 2      | Président CEAM   | + Clôturer un dossier |
| 3      | Administrateur   | + Gérer les rôles des utilisateurs |

## Statuts des dossiers (rappel, valeurs 0 à 4)

0. Nouveau
1. En cours d'instruction
2. Informations complémentaires demandées
3. En attente de décision
4. Clôturé

⚠️ Ces libellés sont une proposition — à confirmer/ajuster selon vos
besoins réels, le champ en base n'est qu'un entier de 0 à 4.

## Index Firestore

Certaines requêtes combinant un filtre `where` et un `order_by` sur un
champ différent peuvent demander la création d'un index composite.
Si une requête échoue avec une erreur du type "The query requires an
index", Firestore fournit directement dans le message un lien pour le
créer en un clic dans la Console.

## Points d'attention à traiter avant mise en production

1. **Noms séparés du plaignant/concerné.** Le modèle `User` ne stocke
   qu'un champ `name` unique, alors que chaque rapport demande nom/prénom
   séparés pour le plaignant et le concerné. Le formulaire de dépôt actuel
   les fait donc ressaisir manuellement plutôt que de les pré-remplir
   automatiquement depuis le compte connecté.
2. **Règles de sécurité Firestore.** Ce projet utilise le SDK Admin côté
   serveur (accès total, contourne les règles de sécurité Firestore) — il
   n'y a donc rien à configurer côté règles tant que seul ce backend Flask
   accède à la base. Si un jour le frontend accède directement à Firestore
   (SDK client), il faudra écrire des règles de sécurité strictes basées
   sur le rôle de l'utilisateur.
3. **Compteur d'ID.** Le compteur auto-incrémenté (`counters/*`) crée un
   point de contention en cas de très fort volume d'écritures simultanées
   (rare ici vu l'usage interne). Si besoin d'un fort débit un jour, migrer
   vers les ID auto-générés natifs de Firestore.
