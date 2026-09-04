#!/usr/bin/env bash
# Wrapper pour lancer dbt avec les variables d'environnement de .env chargées
# (dbt ne lit pas .env automatiquement, contrairement aux scripts Python du projet).
# Usage : ./scripts/dbt.sh seed | ./scripts/dbt.sh run | ./scripts/dbt.sh test ...

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

cd "$ROOT_DIR/dbt_project"
dbt "$@"
