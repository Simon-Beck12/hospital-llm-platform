#!/usr/bin/env bash
# 계정별 LiteLLM 가상 키를 발급한다. 한 번만 실행한다.
# 키 값은 저장소 밖 ~/llm-keys 에 권한 600으로 저장한다. 화면에는 출력하지 않는다.
set -euo pipefail
cd "$(dirname "$0")/.."
MASTER=$(grep '^LITELLM_MASTER_KEY=' .env | cut -d= -f2-)
BASE="http://127.0.0.1:4000"
OUT="$HOME/llm-keys"
install -d -m 700 "$OUT"

issue() {
  local user="$1" rpm="$2" tpm="$3"
  if [ -s "$OUT/$user.key" ]; then
    echo "건너뜀: $OUT/$user.key 이미 있음"
    return
  fi
  curl -sS --fail-with-body "$BASE/key/generate" \
    -H "Authorization: Bearer $MASTER" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"$user\",\"key_alias\":\"$user\",\"models\":[\"qwen3-8b\"],\"rpm_limit\":$rpm,\"tpm_limit\":$tpm,\"duration\":\"30d\"}" \
    | jq -r '.key' > "$OUT/$user.key"
  chmod 600 "$OUT/$user.key"
  echo "발급: $user (rpm=$rpm, tpm=$tpm) -> $OUT/$user.key"
}

issue admin        1000 1000000
issue researcher_a 20   20000
issue researcher_b 5    2000
