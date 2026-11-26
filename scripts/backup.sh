#!/usr/bin/env bash
# LiteLLM DB(키 해시·사용 기록), 감사 로그 볼륨, Grafana 볼륨을 백업한다.
# 출력: ~/llm-backups/<UTC YYYYmmddTHHMMSSZ>/ (폴더 700, 파일 600)
# 운영 컨테이너와 볼륨은 읽기만 한다. .env와 ~/llm-keys는 넣지 않는다. 키·비밀번호는 출력하지 않는다.
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."

PROJECT="${COMPOSE_PROJECT:-llm-platform}"
PG_CONTAINER=litellm-db
TAR_IMAGE=llm-gateway:day2   # 이미 있는 이미지의 tar를 쓴다(새 이미지 받지 않음)
TABLES=(LiteLLM_VerificationToken LiteLLM_UserTable LiteLLM_SpendLogs)
ROOT="$HOME/llm-backups"

start_s=$(date +%s)
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$ROOT/$TS"
show() { echo "${1/#$HOME/\~}"; }

volume_of() {
  local v
  v=$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT" \
    --filter "label=com.docker.compose.volume=$1")
  [ -n "$v" ] || { echo "볼륨 없음: $1" >&2; exit 1; }
  echo "$v"
}
VOL_AUDIT=$(volume_of auditlogs)
VOL_GRAFANA=$(volume_of grafanadata)
PG_USER=$(docker exec "$PG_CONTAINER" printenv POSTGRES_USER)
PG_DB=$(docker exec "$PG_CONTAINER" printenv POSTGRES_DB)

install -d -m 700 "$ROOT"
install -d -m 700 "$OUT"
echo "# 백업 시작 $(date -u +%FT%TZ) -> $(show "$OUT")"

# 1. 행 수(덤프 직전) + PostgreSQL 덤프
declare -A ROWS
for t in "${TABLES[@]}"; do
  ROWS[$t]=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -Atc "select count(*) from \"$t\"")
done
docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc > "$OUT/litellm.dump"
echo "litellm.dump 완료"

# 2. 볼륨 tar (읽기 전용 마운트, 네트워크 없음)
# tar 종료 코드: 0 정상, 1 복사 중 파일 변경(실행 중 복사라 경고로 기록), 2 이상 실패(중단)
WARNINGS=()
vol_tar() {
  local rc=0
  docker run --rm --user 0 --network none -v "$1":/src:ro --entrypoint tar "$TAR_IMAGE" \
    --numeric-owner -C /src -czf - . > "$OUT/$2" || rc=$?
  case "$rc" in
    0) echo "$2 완료" ;;
    1) echo "$2 완료(경고: 복사 중 파일 변경, tar 종료 코드 1)"; WARNINGS+=("$2:file_changed") ;;
    *) echo "$2 실패(tar 종료 코드 $rc)" >&2; exit 1 ;;
  esac
}
vol_tar "$VOL_AUDIT" auditlogs.tar.gz
vol_tar "$VOL_GRAFANA" grafanadata.tar.gz

# 3. manifest
audit_lines=$(tar -xzOf "$OUT/auditlogs.tar.gz" --wildcards '*.jsonl*' | wc -l)
grafana_db_bytes=$(tar -tvzf "$OUT/grafanadata.tar.gz" ./grafana.db | awk '{print $3}')
{
  echo "backup_utc=$TS"
  echo "pg_database=$PG_DB"
  for t in "${TABLES[@]}"; do echo "rows.$t=${ROWS[$t]}"; done
  echo "audit_lines=$audit_lines"
  echo "grafana_db_bytes=$grafana_db_bytes"
  echo "warnings=${WARNINGS[*]:-none}"
  for f in litellm.dump auditlogs.tar.gz grafanadata.tar.gz; do
    echo "file.$f=$(stat -c %s "$OUT/$f")"
  done
} > "$OUT/manifest.txt"

# 4. 체크섬
(cd "$OUT" && sha256sum litellm.dump auditlogs.tar.gz grafanadata.tar.gz manifest.txt > SHA256SUMS)
chmod 600 "$OUT"/*

echo "## manifest"
cat "$OUT/manifest.txt"
echo "## 걸린 시간: $(( $(date +%s) - start_s ))초"
echo "## 폴더: $(show "$OUT")"
