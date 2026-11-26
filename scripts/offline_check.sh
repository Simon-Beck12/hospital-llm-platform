#!/usr/bin/env bash
# 폐쇄망 기동 시험: 인터넷이 끊긴 상태에서 스택을 껐다 켜고, 응답하는지 확인한다.
# 사용: ./scripts/offline_check.sh               (인터넷 차단 상태에서 실행. 연결돼 있으면 종료 코드 2)
#       ./scripts/offline_check.sh --allow-online (온라인 예행연습)
# 종료 코드: 0 통과, 1 실패, 2 시험 무효(인터넷 연결됨)
# sudo를 쓰지 않는다. 키 값은 출력하지 않는다(헤더 파일로만 curl에 넘긴다).
set -u
cd "$(dirname "$0")/.."

MODE=offline
[ "${1:-}" = "--allow-online" ] && MODE=online
OUT="evidence/day4/offline-check-${MODE}.txt"
KEY_FILE="$HOME/llm-keys/researcher_a.key"
GW="http://127.0.0.1:18080"
PROM="http://127.0.0.1:9090"
EXPECTED=7
MAX_WAIT=600
mkdir -p "$(dirname "$OUT")"

ts() { date -u +%FT%TZ; }

main() {
  echo "# 폐쇄망 기동 시험 (mode=$MODE, 시작 $(ts))"

  echo "## 1. 인터넷 차단 확인"
  if curl -sS -m 5 -o /dev/null https://huggingface.co 2>/dev/null; then
    hf="연결됨"
  else
    hf="실패(차단)"
  fi
  echo "curl https://huggingface.co: $hf"
  if dns=$(getent hosts github.com 2>/dev/null); then
    echo "getent hosts github.com: 성공($(echo "$dns" | head -1 | awk '{print $1}'))"
  else
    echo "getent hosts github.com: 실패(정상, DNS 차단)"
  fi
  if [ "$hf" = "연결됨" ] && [ "$MODE" = "offline" ]; then
    echo "인터넷 연결됨: 시험 무효"
    echo "완료"
    return 2
  fi

  echo "## 2. 스택 stop -> start"
  docker compose stop >/dev/null 2>&1
  echo "stop 완료 $(ts)"
  local start_iso start_s
  start_iso=$(ts); start_s=$(date +%s)
  echo "start 시작 $start_iso"
  docker compose start >/dev/null 2>&1 &
  local start_pid=$! ready_s="" el n_ok
  while :; do
    sleep 10
    el=$(( $(date +%s) - start_s ))
    n_ok=0
    for c in $(docker compose ps -a -q); do
      st=$(docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$c")
      case "$st" in "running healthy"|"running none") n_ok=$((n_ok + 1)) ;; esac
    done
    echo "${el}s: 정상 ${n_ok}/${EXPECTED}"
    if [ "$n_ok" -eq "$EXPECTED" ]; then ready_s=$el; break; fi
    [ "$el" -ge "$MAX_WAIT" ] && break
  done
  wait "$start_pid" 2>/dev/null
  docker compose ps -a --format '{{.Name}} {{.Status}}'
  if [ -n "$ready_s" ]; then echo "전부 정상까지: ${ready_s}초"; else echo "전부 정상까지: ${MAX_WAIT}초 안에 안 됨"; fi

  echo "## 3. 게이트웨이 응답 (researcher_a)"
  local hdr whoami chat
  hdr=$(mktemp); chmod 600 "$hdr"
  printf 'Authorization: Bearer %s\n' "$(tr -d '[:space:]' < "$KEY_FILE")" > "$hdr"
  whoami=$(curl -s -o /dev/null -m 15 -w '%{http_code} %{time_total}' -H @"$hdr" "$GW/v1/whoami")
  chat=$(curl -s -o /dev/null -m 60 -w '%{http_code} %{time_total}' -H @"$hdr" -H 'Content-Type: application/json' \
    -d '{"model":"qwen3-8b","messages":[{"role":"user","content":"한 문장으로 인사해줘 /no_think"}],"max_tokens":16}' \
    "$GW/v1/chat/completions")
  rm -f "$hdr"
  echo "whoami: HTTP ${whoami% *}, ${whoami#* }초"
  echo "chat: HTTP ${chat% *}, ${chat#* }초"

  echo "## 4. Prometheus 타깃"
  local targets up_n
  targets=$(curl -s -m 5 "$PROM/api/v1/targets" | jq -c '[.data.activeTargets[] | {job:.labels.job, health}]' 2>/dev/null)
  echo "${targets:-조회 실패}"
  up_n=$(echo "${targets:-[]}" | jq '[.[] | select(.health=="up")] | length' 2>/dev/null)
  echo "타깃 up: ${up_n:-0}/4"

  echo "## 5. 외부 접속 시도 로그 (since $start_iso)"
  local hits benign shown
  hits=$(docker compose logs --no-color --since "$start_iso" 2>&1 \
    | grep -iE 'resolve|connection refused|timed out|huggingface|github|usage|telemetry' \
    | sed -E 's/sk-[A-Za-z0-9_-]+/sk-***/g')
  benign=$(echo "$hits" | grep -cE 'GPU KV cache usage' || true)
  shown=$(echo "$hits" | grep -vE 'GPU KV cache usage' | grep -v '^$')
  echo "패턴 일치 전체: $(echo "$hits" | grep -c . || true)줄 (그중 vLLM KV 캐시 통계 줄 ${benign}줄 제외)"
  echo "외부 접속 시도 의심 줄: $(echo "$shown" | grep -c . || true)줄"
  echo "$shown" | head -30 | cut -c1-240

  echo "## 판정"
  local reason=""
  [ -n "$ready_s" ] || reason="${reason}컨테이너 정상 안 됨, "
  [ "${whoami% *}" = "200" ] || reason="${reason}whoami ${whoami% *}, "
  [ "${chat% *}" = "200" ] || reason="${reason}chat ${chat% *}, "
  if [ -z "$reason" ]; then
    echo "판정: 통과"
    echo "완료"
    return 0
  fi
  echo "판정: 실패(${reason%, })"
  echo "완료"
  return 1
}

main "$@" 2>&1 | tee "$OUT"
exit "${PIPESTATUS[0]}"
