#!/usr/bin/env bash
set -euo pipefail
ROOT="$(dirname "$(realpath "$0")")"
export LAB_DATA_DIR="$ROOT/.lab-data"
export AUTH_PROJECT_DIR="$(realpath "$ROOT/../videojuegos-auth")"
runtime=/tmp/opencode
# Mantener una sola construcción/descarga a la vez en este equipo Live.
export COMPOSE_PARALLEL_LIMIT=1
# Socket y exec-root temporales; imágenes en un ext4 persistente junto al proyecto.
if [[ "${GAMES_ISOLATED_DOCKER:-auto}" == 1 ]] || { [[ "${GAMES_ISOLATED_DOCKER:-auto}" == auto ]] && [[ "$(docker info --format '{{.Driver}}' 2>/dev/null || true)" == vfs ]]; }; then
  mkdir -p "$runtime"
  export DOCKER_HOST="unix://$runtime/games-docker.sock"
  store="$(sudo python3 "$ROOT/scripts/docker_store.py")"
  if docker info >/dev/null 2>&1; then
    actual="$(docker info --format '{{.DockerRootDir}}')"
    if [[ "$actual" != "$store" ]]; then
      printf 'Daemon seleccionado con data-root inesperado: %s (esperado %s). Detén ese daemon antes de continuar.\n' "$actual" "$store" >&2
      exit 1
    fi
  fi
  if ! docker info >/dev/null 2>&1; then
    sudo -v
    sudo env GOMAXPROCS=2 dockerd --config-file="$ROOT/infra/docker-daemon.json" \
      --data-root="$store" --exec-root="$runtime/games-docker-exec" \
      --pidfile="$runtime/games-docker.pid" --host="$DOCKER_HOST" \
      --storage-driver=overlay2 --bridge=none --iptables=false \
      --max-concurrent-downloads=1 --max-concurrent-uploads=1 \
      --containerd-namespace=gameslab --containerd-plugins-namespace=gameslab-plugins \
      --default-address-pool=base=172.29.0.0/16,size=24 \
      >"$runtime/games-dockerd.log" 2>&1 &
    for i in {1..60}; do docker info >/dev/null 2>&1 && break; sleep 1; done
    docker info >/dev/null
  fi
  mkdir -p "$LAB_DATA_DIR"/{ldap-data,ldap-config,keycloak-db,games}
  compose=(docker compose --project-directory "$ROOT" -f "$ROOT/compose.yaml" -f "$AUTH_PROJECT_DIR/compose.yaml" -f "$ROOT/compose.live.yaml")
else
  compose=(docker compose --project-directory "$ROOT" -f "$ROOT/compose.yaml" -f "$AUTH_PROJECT_DIR/compose.yaml")
fi
case "${1:-up}" in
  docker-host) if [[ -n "${DOCKER_HOST:-}" ]]; then printf '%s\n' "$DOCKER_HOST"; else docker context inspect --format '{{.Endpoints.docker.Host}}'; fi ;;
  up)
    shift || true
    if [[ -f "$LAB_DATA_DIR/ldap-data/data.mdb" || -f "$LAB_DATA_DIR/games/games.db" ]]; then
      sudo test -f "$LAB_DATA_DIR/keycloak-db/PG_VERSION" || { printf 'Falta PG_VERSION en un laboratorio existente; restaura el cluster completo antes de arrancar.\n' >&2; exit 1; }
    fi
    python3 "$AUTH_PROJECT_DIR/generate_tls.py" "$LAB_DATA_DIR/tls"
    exec 9>"$runtime/games-build.lock"
    flock -n 9 || { printf 'Ya hay una construcción activa.\n' >&2; exit 1; }
    for service in backend openldap keycloak frontend; do "${compose[@]}" --progress plain build "$service"; done
    "${compose[@]}" up -d --no-build --wait --wait-timeout 420 "$@"
    ;;
  stop) "${compose[@]}" down ;;
  build) shift; flock -n "$runtime/games-build.lock" "${compose[@]}" --progress plain build "$@" ;;
  *) "${compose[@]}" "$@" ;;
esac
