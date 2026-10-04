#!/usr/bin/env bash
#
# Runs on the host, from a clone of this repo with .env filled in. Pulls the
# server image, checks out the commit it was built from (so compose.yaml and
# this script always match the image, a rollback's included), restarts the
# server, and waits until it's healthy. The deploy job in
# .github/workflows/image.yml runs it after every push to main.
#
# Usage: deploy/update.sh [latest | sha-<short commit>]
#   With a tag, pins that tag in .env first. Without one, keeps the current pin
#   (IMAGE_TAG, latest if unset), so a rollback stays in place until someone
#   deploys `latest` again.

set -euo pipefail
cd "$(dirname "$0")/.."

# One deploy at a time: a manual run and an automatic one wait for each other.
# A run that replaced this script re-runs it (see below), passing on the lock
# it holds on fd 9.
if [[ -z "${UPDATE_SH_RERUN:-}" ]]; then
  exec 9> .update.lock
  if ! flock --wait 600 9; then
    echo "update.sh: another deploy has held the lock for 10 minutes; giving up" >&2
    exit 1
  fi
fi

if (( $# > 0 )); then
  if ! [[ "$1" =~ ^(latest|sha-[0-9a-f]{7,40})$ ]]; then
    echo "update.sh: the tag must be 'latest' or 'sha-<commit>', not '$1'" >&2
    exit 2
  fi
  # Replace IMAGE_TAG and keep every other setting. .env holds secrets, so the
  # new copy is private to this user too.
  (umask 077 && { grep -v '^IMAGE_TAG=' .env || true; echo "IMAGE_TAG=$1"; } > .env.new)
  mv .env.new .env
fi

image=$(docker compose config --images)
echo "Deploying $image"
docker pull --quiet "$image" >/dev/null

# Switch the checkout to the commit the image was built from. Git replaces
# files rather than rewriting them, so this running copy of the script is safe.
revision=$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image")
script_before=$(git hash-object deploy/update.sh)
git fetch --quiet origin
git checkout --quiet --detach "$revision"
echo "Checked out ${revision:0:7}"

# bash reads a script as it runs, and this one is the old version. Let the new
# version do the rest of the deploy, once. (An older commit may not have it.)
script_after=$(git hash-object deploy/update.sh 2>/dev/null || true)
if [[ -n "$script_after" && "$script_after" != "$script_before" && -z "${UPDATE_SH_RERUN:-}" ]]; then
  echo "Re-running the new update.sh"
  UPDATE_SH_RERUN=1 exec deploy/update.sh "$@"
fi

if ! docker compose up --detach --wait --wait-timeout 120; then
  echo "update.sh: the server didn't become healthy. Its last log lines:" >&2
  docker compose logs --tail 50 >&2
  exit 1
fi
echo "Healthy: running commit ${revision:0:7}"

# Remove this server's images no container uses (the old latest, or a sha- tag
# rolled back from) to save disk space. A rollback pulls its tag again.
source=$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.source"}}' "$image")
docker image prune --all --force --filter "label=org.opencontainers.image.source=$source" >/dev/null
