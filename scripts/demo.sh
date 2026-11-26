#!/usr/bin/env bash
# 녹화용 시연 스크립트. 장면 7개를 순서대로 보여 준다.
# 사용: ./scripts/demo.sh            (장면마다 Enter로 넘김)
#       DEMO_AUTO=1 ./scripts/demo.sh (멈추지 않고 끝까지)
# 키는 600 임시 헤더 파일로만 curl에 넘기고 끝나면 지운다. 키 값은 출력하지 않는다. PII는 가짜 값이다.
set -u
cd "$(dirname "$0")/.."

GW="http://127.0.0.1:18080"
PROM="http://127.0.0.1:9090"
KEYS="$HOME/llm-keys"
TMPD=$(mktemp -d)
chmod 700 "$TMPD"
trap 'rm -rf "$TMPD"' EXIT

hdr() {  # hdr <계정> -> 헤더 파일 경로
  local f="$TMPD/$1.hdr"
  if [ ! -f "$f" ]; then
    (umask 077; printf 'Authorization: Bearer %s\n' "$(tr -d '[:space:]' < "$KEYS/$1.key")" > "$f")
  fi
  echo "$f"
}

scene() {  # scene <번호> <제목> <설명>
  echo
  echo "=================================================================="
  echo "[장면 $1] $2"
  echo "  $3"
  echo "=================================================================="
}

pause() {
  if [ "${DEMO_AUTO:-0}" != "1" ]; then
    read -r -p "Enter: 다음 " _
  fi
}

chat_body() {  # chat_body <내용> <max_tokens>
  jq -cn --arg c "$1" --argjson m "$2" '{model:"qwen3-8b", messages:[{role:"user", content:$c}], max_tokens:$m}'
}

scene 1 "스택 상태" "Docker Compose 7개 서비스가 떠 있고, healthcheck가 있는 3개는 healthy인지 본다."
docker compose ps --format 'table {{.Name}}\t{{.Status}}'
pause

scene 2 "계정 식별" "게이트웨이는 마스터 키 없이, 요청자 본인 키로 LiteLLM에 물어 계정을 알아낸다."
curl -s -H @"$(hdr researcher_a)" "$GW/v1/whoami" | jq .
pause

scene 3 "PII 마스킹" "주민번호·전화번호를 모델에 보내기 전에 가린다. 응답 헤더 X-PII-Masked에 건수가 나온다(가짜 값)."
body=$(chat_body "가짜 환자 홍길동, 주민번호 900101-1234567, 연락처 010-1234-5678 을 요약해줘 /no_think" 64)
curl -s -D "$TMPD/h3" -o "$TMPD/b3" -H @"$(hdr researcher_a)" -H 'Content-Type: application/json' \
  -d "$body" "$GW/v1/chat/completions"
echo "HTTP $(head -1 "$TMPD/h3" | awk '{print $2}')"
grep -iE '^(x-pii-masked|x-request-id):' "$TMPD/h3" | tr -d '\r'
content=$(jq -r '.choices[0].message.content // .error.message // empty' "$TMPD/b3")
echo "응답 본문 앞 200자: ${content:0:200}"
pause

scene 4 "사용량 한도" "researcher_b는 분당 5회 한도다. 7회 연속 보내면 6회째부터 429와 Retry-After가 나온다."
echo "researcher_b는 분당 5회 한도"
body=$(chat_body "안녕 /no_think" 8)
for i in 1 2 3 4 5 6 7; do
  code=$(curl -s -D "$TMPD/h4" -o /dev/null -w '%{http_code}' -H @"$(hdr researcher_b)" \
    -H 'Content-Type: application/json' -d "$body" "$GW/v1/chat/completions")
  ra=$(grep -i '^retry-after:' "$TMPD/h4" | tr -d '\r' | awk '{print $2}')
  if [ "$code" = "429" ]; then echo "$i회: HTTP $code, Retry-After: ${ra:-없음}초"; else echo "$i회: HTTP $code"; fi
done
pause

scene 5 "감사 로그" "요청마다 JSON 한 줄을 남긴다. 프롬프트 본문은 없고, 마스킹 후 해시(prompt_sha256)만 남는다."
docker exec llm-gateway tail -n 3 /app/logs/audit.jsonl \
  | jq -c '{ts, user_id, key_alias, status, pii_counts, prompt_sha256}'
pause

scene 6 "알림 규칙" "Prometheus 알림 규칙 4개의 상태(inactive/pending/firing)와 health를 본다."
curl -s "$PROM/api/v1/rules" | jq -r '.data.groups[].rules[] | "\(.name)\t\(.state)\t\(.health)"'
pause

scene 7 "대시보드" "브라우저에서 Grafana 대시보드(http://127.0.0.1:3000/d/llm-platform)를 보여 주세요"
echo "시연 끝"
