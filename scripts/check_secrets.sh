#!/usr/bin/env bash
# Git 이력 전체에서 비밀정보를 검사한다. 결과는 가린다(--redact).
set -euo pipefail
cd "$(dirname "$0")/.."
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/repo:ro" zricethezav/gitleaks:v8.30.1 git --redact --no-banner -v /repo
