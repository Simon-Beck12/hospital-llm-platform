# 백업과 복구 (2026-11-26)

- [scripts/backup.sh](../scripts/backup.sh)가 운영 데이터를 `~/llm-backups/<UTC 시각>/`에 백업한다. 운영 컨테이너와 볼륨은 읽기만 한다.
- [scripts/restore_test.sh](../scripts/restore_test.sh)는 그 백업을 임시 컨테이너에 복구해, 백업할 때 기록한 숫자와 같은지 확인한다.

```bash
./scripts/backup.sh                                  # 백업 1세트 생성, 마지막에 폴더 경로 출력
./scripts/restore_test.sh ~/llm-backups/<시각>       # 임시 컨테이너 복구 시험, "판정: 통과/실패"
```

## 백업 대상

| 대상 | 방식 | 파일 | 백업 시점 크기 | 담긴 것 |
|---|---|---|---|---|
| PostgreSQL(LiteLLM) | `docker exec litellm-db pg_dump -Fc` | litellm.dump | 1,194,836 B (1.1 MiB) | 가상 키의 해시·한도·만료(VerificationToken 4행), 사용 기록(SpendLogs 3,157행), 사용자 테이블(0행) |
| 감사 로그 볼륨 | 읽기 전용 마운트 + tar.gz(`--network none`) | auditlogs.tar.gz | 120,145 B (117 KiB) | 게이트웨이 감사 로그 3,127줄(JSON, 17필드) |
| Grafana 볼륨 | 읽기 전용 마운트 + tar.gz(`--network none`) | grafanadata.tar.gz | 127,551,843 B (122 MiB) | grafana.db(1,699,840 B, admin 계정과 설정), 설치된 플러그인(383 MiB, 압축 전) |
| 메타데이터 | 스크립트가 생성 | manifest.txt, SHA256SUMS | 306 B, 326 B | 백업 시각, 행 수, 감사 로그 줄 수, 파일 크기, 경고 / 체크섬 |

- tar는 운영 이미지 `llm-gateway:day2`에 들어 있는 것을 쓴다. 새 이미지를 받지 않는다.

## 백업하지 않는 것과 이유

| 대상 | 이유 |
|---|---|
| `.env`, `~/llm-keys` | 비밀정보는 따로 보관한다. 백업 폴더에 사본을 만들어 퍼뜨리지 않는다. |
| 모델 파일(`/srv/models`, 약 16 GB) | 원본(배포처나 반입 매체)에서 다시 복사하면 된다. |
| Prometheus 지표(promdata) | 15일만 보존하는 데이터이고, 다시 수집할 수 있다. 장기 기록은 감사 로그와 SpendLogs에 남는다. |
| Grafana 대시보드 | `monitoring/grafana/`의 코드로 프로비저닝한다. 저장소가 원본이다. |

## 보안

- 백업 폴더는 700, 파일은 600이다. 스크립트가 `umask 077`과 `chmod 600`으로 맞춘다.
- 덤프 안에서 실제 키 문자열을 찾아보니 4개 키 모두 0건이었다([backup-key-check.txt](../evidence/day4/backup-key-check.txt)). VerificationToken.token은 64자리 16진수 해시다.
- 그래도 덤프에는 키 해시, 한도, 사용자별 사용 기록이 들어 있다. 감사 로그에는 사용자, 시각, 프롬프트 해시가 들어 있다. 그래서 백업 전체를 민감 자료로 다룬다.

## 실측 (2026-11-26)

| 항목 | 값 |
|---|---|
| 백업 시간 | 14초(1.1 MiB 덤프 + 122 MiB tar) |
| 복구 시험 시간 | 11초 |
| 일치 항목 | 9/9: 무결성, PG 행 수 3개, 감사 로그 줄 수, 첫 줄 JSON, grafana.db 크기, Grafana DB, admin 로그인 |

- 원본: [backup-run.txt](../evidence/day4/backup-run.txt), [restore-run.txt](../evidence/day4/restore-run.txt)
- 첫 실행의 기록은 [backup-run-attempt1.txt](../evidence/day4/backup-run-attempt1.txt)에 있다. Grafana tar의 종료 코드 1(복사 중 파일 변경)을 스크립트가 놓쳐서 고쳤다. 지금은 종료 코드 1은 manifest에 `warnings`로 남기고, 2 이상이면 중단한다.

## 운영 복구 절차 (문서만, 이번에는 실행 안 함)

1. 스택을 멈춘다: `docker compose stop`
2. 볼륨을 복원한다. 감사 로그와 Grafana 볼륨을 비운 뒤 백업 tar를 푼다.
   `docker run --rm --user 0 --network none -v llm-platform_grafanadata:/dst -v <백업>:/b:ro --entrypoint tar llm-gateway:day2 --numeric-owner -C /dst -xzpf /b/grafanadata.tar.gz`
   auditlogs도 같은 방식으로 푼다.
3. DB를 복원한다: `docker compose start db`를 실행한 뒤 `docker exec -i litellm-db pg_restore -U litellm -d litellm --clean --if-exists --no-owner < <백업>/litellm.dump`
4. 나머지를 기동한다: `docker compose start`
5. 확인한다:
   - `docker compose ps`에서 7개가 정상인지 본다.
   - 각 키로 `/key/info`를 조회해 한도가 [quota-policy.md](quota-policy.md)와 같은지 본다.
   - 게이트웨이 `/v1/whoami`와 chat이 200인지 본다.
   - Grafana `/api/health`가 ok인지 본다.

- 주의: `.env`의 `LITELLM_SALT_KEY`가 백업할 때와 같아야 한다. 다르면 DB에 암호화돼 저장된 값을 풀 수 없다.

## 주기 제안 (이번에는 설치 안 함)

- cron으로 매일 1회(예: 03:00 KST) `scripts/backup.sh`를 돌리고, 가장 최근 7세트를 보관한다. 1세트가 약 123 MiB라 7세트는 약 0.9 GiB다.
- RPO(잃을 수 있는 데이터)는 최대 24시간이다. RTO(복구 시간)는 약 5분으로 추정한다. 근거는 복구 시험 11초, 스택 기동 61초(폐쇄망 시험 실측), 확인 수 분이다.

## 한계

- Grafana 볼륨은 컨테이너가 실행 중일 때 복사한다. tar가 "file changed as we read it"를 냈지만, 대시보드는 코드로 관리하고 Grafana는 거의 유휴 상태라 일관성 문제는 낮다. 이번 복구 시험에서도 DB ok와 로그인 200을 확인했다.
- 백업이 운영과 같은 디스크(`~/llm-backups`)에 있다. 디스크가 고장 나면 백업도 함께 잃는다. 실제 운영에서는 별도 저장소(NAS, 외부 매체)로 복사해야 한다.
