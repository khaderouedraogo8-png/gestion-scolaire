#!/bin/sh
set -e

echo "Initialisation des données..."
flask --app run.py seed || echo "Seed déjà effectué ou erreur ignorée"

echo "Démarrage du serveur Flask..."
exec flask --app run.py run --host 0.0.0.0 --port 5000 --debug
