# ASF Benev

Portail benevole pour declarer les disponibilites et gerer les contraintes.

## Stack
- Django + Django REST Framework
- Admin Django pour la gestion des benevoles
- API REST + export CSV pour `asf-scheduler` et `asf-wms`

## Demarrage rapide
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 manage.py makemigrations accounts volunteers
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py runserver
```

Ouvrir http://127.0.0.1:8000/ puis se connecter.

## Creation des benevoles
Via l'admin Django :
1. Creer un compte utilisateur (email + mot de passe).
2. Renseigner le profil benevole (ID immuable, prenom court, telephone).

## Configuration base de donnees
Par defaut, SQLite est utilise. Pour Postgres, definir :
```bash
export DB_ENGINE=django.db.backends.postgresql
export DB_NAME=asf_benev
export DB_USER=asf_benev
export DB_PASSWORD=secret
export DB_HOST=localhost
export DB_PORT=5432
```

Le fuseau horaire applicatif est configure sur `Europe/Paris`.

## Diffuser a tous (deploiement gratuit)
Suggestion gratuite avec sous-domaine fourni :
- App Django : Render (free web service)
- Base de donnees : Neon Postgres (free, region Europe)
- Emails (mot de passe oublie) : Brevo SMTP (free tier)

Le fichier `render.yaml` permet de creer le service Render automatiquement (Docker). Le `Dockerfile` est fourni si vous preferez un deploiement conteneurise ailleurs.
Sur Render : New > Blueprint, selectionner le repo, puis renseigner les variables d'environnement.

Variables d'environnement a configurer sur l'hebergeur :
```
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=0
DB_ENGINE=django.db.backends.postgresql
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_USE_TLS=1
EMAIL_USE_SSL=0
EMAIL_TIMEOUT=10
DEFAULT_FROM_EMAIL=asf-benev@exemple.org
```

Sur Render, `RENDER_EXTERNAL_HOSTNAME` est ajoute automatiquement dans `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS`.

Commandes de build/launch (Render) :
```
python3 manage.py migrate
python3 manage.py collectstatic --noinput
gunicorn asf_benev.wsgi:application
```

Ensuite, partager le lien public (sous-domaine) a tous les benevoles.

Sur Render (free, sans shell), les migrations et la creation d'admin sont lancees automatiquement par le conteneur si vous renseignez :
```
DJANGO_SUPERUSER_EMAIL=admin@exemple.org
DJANGO_SUPERUSER_PASSWORD=MotDePasseSolide
DJANGO_SUPERUSER_FIRST_NAME=Admin
DJANGO_SUPERUSER_LAST_NAME=ASF
```
Le superuser est cree si besoin (commande `ensure_admin`).

## Import Excel / CSV
```bash
python3 manage.py import_volunteers /chemin/volunteers.xlsx --default-password "TempPass123"
```
Options :
- `--update` pour mettre a jour les benevoles existants
- `--dry-run` pour tester sans enregistrer

Colonnes attendues : `ID`, `NOM`, `PRENOM`, `PRENOM_COURT`, `MAX_JOURS_SEMAINE`, `MAX_EXP_SEMAINE`, `MAX_EXP_JOUR`, `ATTENTE_MAX_H`, `Telephone`, `Mail`.

## API d'integration
Creer un compte technique staff (admin) et un token DRF :
```bash
python3 manage.py drf_create_token <email>
```
Utiliser le token dans `Authorization: Token <token>`.

Endpoints principaux :
- `GET /api/integrations/volunteers/`
- `GET /api/integrations/availabilities/?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `GET /api/integrations/volunteers.csv`
- `GET /api/integrations/availabilities.csv?start=YYYY-MM-DD&end=YYYY-MM-DD`

## Mot de passe oublie
Le lien est disponible sur l'ecran de connexion. Configurez l'envoi SMTP via les variables ci-dessus.

## Emails d'invitation
Envoyer un email de creation de mot de passe a tous les benevoles :
```bash
python3 manage.py send_invitations --domain ton-app.onrender.com
```
Options utiles :
- `--dry-run` pour verifier les liens
- `--emails mail1@mail.com mail2@mail.com` pour cibler
- `--volunteer-ids 7 16 8` pour cibler

Si Render n'a pas de shell, lancez ces commandes en local en pointant vers la base Neon (variables DB_*) et en configurant SMTP (EMAIL_*).

## RGPD (bonnes pratiques)
- Donnees strictement necessaires (coordonnees, contraintes, disponibilites).
- Acces limite par comptes individuels, tokens pour integrations.
- Suppression possible via admin (profil, disponibilites, contraintes).
