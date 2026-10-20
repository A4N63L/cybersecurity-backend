#!/usr/bin/env bash
set -euo pipefail
ROOT="$(dirname "$(realpath "$0")")"
export LAB_DATA_DIR="$ROOT/.lab-data"
runtime=/tmp/opencode
# El sistema Live usa vfs. Un daemon overlay2 propio evita copiar todas las
# capas en el USB; el daemon anterior permanece intacto. Datos en .lab-data.
if [[ "${GAMES_ISOLATED_DOCKER:-auto}" == 1 ]] || { [[ "${GAMES_ISOLATED_DOCKER:-auto}" == auto ]] && [[ "$(docker info --format '{{.Driver}}' 2>/dev/null || true)" == vfs ]]; }; then
  mkdir -p "$runtime"
  export DOCKER_HOST="unix://$runtime/games-docker.sock"
  if ! docker info >/dev/null 2>&1; then
    sudo -v
    sudo dockerd --config-file="$ROOT/infra/docker-daemon.json" \
      --data-root="$runtime/games-docker-data" --exec-root="$runtime/games-docker-exec" \
      --pidfile="$runtime/games-docker.pid" --host="$DOCKER_HOST" \
      --storage-driver=overlay2 --bridge=none --iptables=false \
      --containerd-namespace=gameslab --containerd-plugins-namespace=gameslab-plugins \
      --default-address-pool=base=172.29.0.0/16,size=24 \
      >"$runtime/games-dockerd.log" 2>&1 &
    for i in {1..60}; do docker info >/dev/null 2>&1 && break; sleep 1; done
    docker info >/dev/null
  fi
  mkdir -p "$LAB_DATA_DIR"/{ldap-data,ldap-config,keycloak-db,games}
  compose=(docker compose --project-directory "$ROOT" -f "$ROOT/compose.yaml" -f "$ROOT/compose.live.yaml")
else
  compose=(docker compose --project-directory "$ROOT" -f "$ROOT/compose.yaml")
fi
case "${1:-up}" in
  up) shift || true; "${compose[@]}" up -d --build --wait --wait-timeout 420 "$@" ;;
  stop) "${compose[@]}" down ;;
  *) "${compose[@]}" "$@" ;;
esac
