#!/usr/bin/env bash
# 백업을 임시 컨테이너에 복구해 manifest의 숫자와 비교한다. 운영 컨테이너·볼륨은 건드리지 않는다.
# 사용: ./scripts/restore_test.sh ~/llm-backups/<시각>
# 종료 코드: 0 통과, 1 실패. 끝날 때 임시 컨테이너 2개, 임시 볼륨, 임시 파일을 항상 지운다.
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."

DIR="${1:?사용: $0 <백업 폴더>}"
DIR=$(cd "$DIR" && pwd)
PG_C=pg-restore-test
GF_C=grafana-restore-test
GF_VOL=grafana-restore-test-data
GF_PORT=13000
TAR_IMAGE=llm-gateway:day2
TABLES=(LiteLLM_VerificationToken LiteLLM_UserTable LiteLLM_SpendLogs)
start_s=$(date +%s)
show() { echo "${1/#$HOME/\~}"; }
mf() { grep "^$1=" "$DIR/manifest.txt" | cut -d= -f2-; }

# 같은 이름의 자원이 이미 있으면 지우지 않고 멈춘다.
if docker ps -a --format '{{.Names}}' | grep -qxE "$PG_C|$GF_C" || docker volume inspect "$GF_VOL" >/dev/null 2>&1; then
  echo "임시 자원이 이미 있음($PG_C/$GF_C/$GF_VOL). 확인 후 다시 실행" >&2
  exit 1
fi

TMPD=$(mktemp -d)
cleanup() {
  docker rm -f "$PG_C" "$GF_C" >/dev/null 2>&1 || true
  docker volume rm "$GF_VOL" >/dev/null 2>&1 || true
  rm -rf "$TMPD"
}
trap cleanup EXIT

declare -a RESULT   # "항목|백업|복구|결과"
add() { RESULT+=("$1|$2|$3|$([ "$2" = "$3" ] && echo 일치 || echo 불일치)"); }

echo "# 복구 시험 시작 $(date -u +%FT%TZ), 백업 $(show "$DIR")"

# a. 무결성
echo "## a. 무결성"
if (cd "$DIR" && sha256sum -c --quiet SHA256SUMS); then sums=ok; else sums=fail; fi
echo "sha256sum -c: $sums"
add "무결성(SHA256SUMS)" ok "$sums"

# b. PostgreSQL
echo "## b. PostgreSQL ($PG_C, --network none)"
PGPASS=$(openssl rand -hex 16)
docker run -d --name "$PG_C" --network none -e POSTGRES_PASSWORD="$PGPASS" postgres:16.16 >/dev/null
unset PGPASS
ready=""
for _ in $(seq 1 60); do
  if docker logs "$PG_C" 2>&1 | grep -q 'PostgreSQL init process complete' \
     && docker exec "$PG_C" pg_isready -U postgres -q 2>/dev/null; then ready=1; break; fi
  sleep 1
done
[ -n "$ready" ] || { echo "PostgreSQL 60초 안에 준비 안 됨"; }
echo "pg_isready: ${ready:+ok}"
pg_rc=0
if [ -n "$ready" ]; then
  docker cp "$DIR/litellm.dump" "$PG_C:/tmp/litellm.dump" >/dev/null
  docker exec "$PG_C" pg_restore -U postgres -d postgres -C --no-owner --no-privileges /tmp/litellm.dump \
    > "$TMPD/pg_restore.log" 2>&1 || pg_rc=$?
  echo "pg_restore 종료 코드: $pg_rc, 오류 줄: $(grep -c 'error:' "$TMPD/pg_restore.log" || true)"
fi
db=$(mf pg_database)
for t in "${TABLES[@]}"; do
  got=$(docker exec "$PG_C" psql -U postgres -d "$db" -Atc "select count(*) from \"$t\"" 2>/dev/null || echo "조회 실패")
  add "PG 행 수 $t" "$(mf "rows.$t")" "$got"
done

# c. 감사 로그
echo "## c. 감사 로그"
lines=$(tar -xzOf "$DIR/auditlogs.tar.gz" --wildcards '*.jsonl*' | wc -l)
add "감사 로그 줄 수" "$(mf audit_lines)" "$lines"
first=$(tar -xzOf "$DIR/auditlogs.tar.gz" ./audit.jsonl 2>/dev/null | head -n1 || true)
if echo "$first" | jq -e 'has("request_id")' >/dev/null 2>&1; then json=ok; else json=fail; fi
echo "첫 줄 JSON 파싱: $json (필드 수 $(echo "$first" | jq 'length' 2>/dev/null || echo 0))"
add "감사 로그 첫 줄 JSON" ok "$json"

# d. Grafana
echo "## d. Grafana ($GF_C, 127.0.0.1:$GF_PORT)"
docker volume create "$GF_VOL" >/dev/null
docker run --rm --user 0 --network none -v "$GF_VOL":/dst -v "$DIR":/b:ro --entrypoint tar "$TAR_IMAGE" \
  --numeric-owner -C /dst -xzpf /b/grafanadata.tar.gz
gdb=$(docker run --rm --network none -v "$GF_VOL":/dst:ro --entrypoint stat "$TAR_IMAGE" -c %s /dst/grafana.db)
add "grafana.db 크기(바이트)" "$(mf grafana_db_bytes)" "$gdb"
docker run -d --name "$GF_C" -p "127.0.0.1:$GF_PORT:3000" -v "$GF_VOL":/var/lib/grafana \
  -e GF_ANALYTICS_REPORTING_ENABLED=false -e GF_ANALYTICS_CHECK_FOR_UPDATES=false \
  -e GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false -e GF_NEWS_NEWS_FEED_ENABLED=false \
  -e GF_PLUGINS_PREINSTALL_DISABLED=true \
  grafana/grafana:13.3.1 >/dev/null
health=fail
for _ in $(seq 1 90); do
  h=$(curl -s -m 2 "127.0.0.1:$GF_PORT/api/health" | jq -r '.database // empty' 2>/dev/null || true)
  [ "$h" = "ok" ] && { health=ok; break; }
  sleep 1
done
echo "api/health database: $health"
add "Grafana DB(api/health)" ok "$health"
NETRC="$TMPD/netrc"
printf 'machine 127.0.0.1 login admin password %s\n' "$(grep '^GRAFANA_ADMIN_PASSWORD=' .env | cut -d= -f2-)" > "$NETRC"
chmod 600 "$NETRC"
login=$(curl -s -o /dev/null -m 5 -w '%{http_code}' --netrc-file "$NETRC" "http://127.0.0.1:$GF_PORT/api/user" || true)
rm -f "$NETRC"
echo "admin 로그인 /api/user: $login"
add "Grafana admin 로그인(/api/user)" 200 "$login"

# e. 결과
echo "## 결과"
echo "| 항목 | 백업 | 복구 | 결과 |"
echo "|---|---|---|---|"
fails=()
for r in "${RESULT[@]}"; do
  IFS='|' read -r name want got res <<< "$r"
  echo "| $name | $want | $got | $res |"
  [ "$res" = "일치" ] || fails+=("$name")
done
echo "일치 ${#RESULT[@]}개 중 $(( ${#RESULT[@]} - ${#fails[@]} ))개"
echo "걸린 시간: $(( $(date +%s) - start_s ))초"
if [ ${#fails[@]} -eq 0 ]; then
  echo "판정: 통과"
  exit 0
fi
echo "판정: 실패($(IFS=,; echo "${fails[*]}"))"
exit 1
