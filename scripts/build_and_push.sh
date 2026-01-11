#!/usr/bin/env bash
set -euo pipefail

IMAGE_BASE="henfri/uvr2mqtt"
VERSION=${1:-}

if [[ -z "${VERSION}" ]]; then
  echo "Usage: $0 <version>" >&2
  exit 1
fi

# Build with both tags
DOCKER_BUILDKIT=1 docker build -t "${IMAGE_BASE}:${VERSION}" -t "${IMAGE_BASE}:latest" .

# Push only if build succeeded
for TAG in "${VERSION}" latest; do
  docker push "${IMAGE_BASE}:${TAG}"
done
