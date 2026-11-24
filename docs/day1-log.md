# 1일차 작업 기록

날짜: 2026-11-23

## 1단계 사전 점검

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| OS | Ubuntu 24.04.x | Ubuntu 24.04.5 LTS (커널 7.0.0-43-generic) | 통과 |
| GPU | RTX 5090, 약 32GB (32607 MiB 전후) | NVIDIA GeForce RTX 5090, 32607 MiB | 통과 |
| 드라이버 | 570 이상 | 580.178.04 | 통과 |
| CUDA Version | 12.8 이상 | 13.0 | 통과 |
| GPU 기존 사용량 | 1GB 이하 권장 | 2444 MiB (Xorg 1016, chrome 582, steamwebhelper 257, gnome-shell 173, code 160, obsidian 102 등). compute 프로세스 0개 | 미달 (비고: vLLM 실행 전 chrome·steam 종료 예정) |
| 루트 디스크 여유 | 100GB 이상 | 1009G 가용 / 1.8T (42% 사용). /srv는 루트와 같은 파티션 | 통과 |
| RAM | 128GB 전후 | 125 GiB (free -g), 가용 115 GiB. CPU 32코어 | 통과 |
| jq/curl/git/openssl/uv | 설치됨 | jq 1.7, curl 8.5.0, git 2.43.0, OpenSSL 3.0.13, uv 0.13.6 | 통과 |
| docker | 4단계 설치 예정이면 "없음"도 정상 | Docker 29.9.3 설치됨 | 통과 |
| nvidia-ctk | 4단계 설치 예정이면 "없음"도 정상 | 없음 | 통과 |
| openssh-server | 3단계 설치 예정이면 "없음"도 정상 | 없음 (dpkg: un, ssh inactive) | 통과 |

메모
- GPU 기존 사용량 2444 MiB는 데스크톱 그래픽 프로세스(G 타입)다. vLLM 기동 시 `--gpu-memory-utilization`을 낮추거나 chrome/steam/obsidian을 닫아야 한다.
- 잘린 프로세스 이름은 `ps -o pid,comm`으로 확인: 7021=chrome, 7140=code, 7980=steamwebhelper, 15809=obsidian.

### 원본 출력

```text
### OS
$ lsb_release -d
Description:	Ubuntu 24.04.5 LTS

$ uname -r
7.0.0-43-generic

$ nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu --format=csv
name, driver_version, memory.total [MiB], memory.used [MiB], temperature.gpu
NVIDIA GeForce RTX 5090, 580.178.04, 32607 MiB, 2444 MiB, 42

$ nvidia-smi | head -4
Mon Nov 23 20:31:21 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.178.04             Driver Version: 580.178.04     CUDA Version: 13.0     |
+-----------------------------------------+------------------------+----------------------+

$ nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
pid, process_name, used_gpu_memory [MiB]

$ nvidia-smi
Mon Nov 23 20:31:22 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.178.04             Driver Version: 580.178.04     CUDA Version: 13.0     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 5090        Off |   00000000:0B:00.0  On |                  N/A |
|  0%   42C    P0             47W /  575W |    2444MiB /  32607MiB |      4%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A            5800      G   /usr/lib/xorg/Xorg                     1016MiB |
|    0   N/A  N/A            6050      G   /usr/bin/gnome-shell                    173MiB |
|    0   N/A  N/A            7021      G   ...rack-uuid=3190708988185955192        582MiB |
|    0   N/A  N/A            7140      G   ...rack-uuid=3190708988185955192        160MiB |
|    0   N/A  N/A            7643      G   ...l/share/Steam/steamrt64/steam         13MiB |
|    0   N/A  N/A            7891      G   ./steamwebhelper                          8MiB |
|    0   N/A  N/A            7980      G   ...team/steamrt64/steamwebhelper        257MiB |
|    0   N/A  N/A           15809      G   ...708988185955192 --log-level=3        102MiB |
+-----------------------------------------------------------------------------------------+

$ df -h /
파일 시스템     크기  사용  가용 사용% 마운트위치
/dev/nvme1n1p2  1.8T  730G 1009G   42% /

$ df -h /srv 2>/dev/null
파일 시스템     크기  사용  가용 사용% 마운트위치
/dev/nvme1n1p2  1.8T  730G 1009G   42% /

$ free -g
               총계         사용        여분      공유    버퍼/캐시    가용
메모리:          125          10         108           0           8         115
스  왑:            7           0           7

$ nproc
32

$ command -v jq
/usr/bin/jq

$ command -v curl
/usr/bin/curl

$ command -v git
/usr/bin/git

$ command -v openssl
/usr/bin/openssl

$ command -v uv
/home/beck/.local/bin/uv

$ command -v docker
/usr/bin/docker

$ command -v nvidia-ctk

$ jq --version
jq-1.7

$ curl --version | head -1
curl 8.5.0 (x86_64-pc-linux-gnu) libcurl/8.5.0 OpenSSL/3.0.13 zlib/1.3 brotli/1.1.0 zstd/1.5.5 libidn2/2.3.7 libpsl/0.21.2 (+libidn2/2.3.7) libssh/0.10.6/openssl/zlib nghttp2/1.59.0 librtmp/2.3 OpenLDAP/2.6.10

$ git --version
git version 2.43.0

$ openssl version
OpenSSL 3.0.13 30 Jan 2024 (Library: OpenSSL 3.0.13 30 Jan 2024)

$ uv --version
uv 0.13.6 (x86_64-unknown-linux-gnu)

$ docker --version
Docker version 29.9.3, build 5457199

$ nvidia-ctk --version
bash: 줄 1: nvidia-ctk: 명령어를 찾을 수 없음

$ systemctl is-active ssh
inactive

$ dpkg -l openssh-server | tail -1
un  openssh-server <none>       <none>       (설명 없음)

$ ps -o pid,comm -p 7021,7140,15809,7980
    PID COMMAND
   7021 chrome
   7140 code
   7980 steamwebhelper
  15809 obsidian
```

## 2단계 계정과 모델

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| admin 그룹 | sudo, llm-admins, docker 포함 | sudo, docker, llm-admins, users | 통과 |
| researcher_a 그룹 | llm-users 포함, sudo·docker 없음 | llm-users, users | 통과 |
| researcher_b 그룹 | llm-users 포함, sudo·docker 없음 | llm-users, users | 통과 |
| beck 그룹 | llm-admins 포함 | sudo, docker, llm-admins 외 | 통과 |
| 홈 권한 | drwxr-x--- (750) | /home/admin, researcher_a, researcher_b 모두 drwxr-x--- | 통과 |
| /srv/models 권한 | drwxrwsr-x, beck:llm-admins | drwxrwsr-x beck llm-admins | 통과 |
| 가중치 파일 일치 | index.json weight_map과 diff 없음 | 5개 일치 (model-0000{1..5}-of-00005), config/tokenizer/generation_config 존재 | 통과 |
| 모델 크기 | 15~17G | 16G (du -sh), 16,397,465,974 bytes | 통과 |
| 다운로드 소요 시간 | 30분 이내 | 약 4분 (20:44:30 시작 → 20:48:34 로그 마지막 기록) | 통과 |
| 서버 IP | 조회됨 | enp6s0 172.30.1.44/24 | 통과 |

메모
- hf CLI: huggingface_hub 2.4.0 (`uv tool install`, `hf version` → version=2.4.0). 2.4.0에는 `[cli]` extra가 없어 경고가 났지만 hf는 설치됨.
- 다운로드 PID 138853, 토큰 없이 받음. 로그에 `.gitignore.lock` 대기 메시지(0.1초)가 있었으나 오류 없이 끝남.
- 서버 IP 목록의 br-e5378fa6218e(172.18.0.1), docker0(172.17.0.1)는 Docker 브리지다.

### 원본 출력

```text
$ for u in beck admin researcher_a researcher_b; do id "$u"; done
uid=1000(beck) gid=1000(beck) groups=1000(beck),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),100(users),114(lpadmin),984(docker),1001(llm-admins)
uid=1003(admin) gid=1003(admin) groups=1003(admin),27(sudo),100(users),984(docker),1001(llm-admins)
uid=1004(researcher_a) gid=1004(researcher_a) groups=1004(researcher_a),100(users),1002(llm-users)
uid=1005(researcher_b) gid=1005(researcher_b) groups=1005(researcher_b),100(users),1002(llm-users)

$ ls -ld /home/admin /home/researcher_a /home/researcher_b
drwxr-x--- 2 admin        admin        4096 11월 23 20:41 /home/admin
drwxr-x--- 2 researcher_a researcher_a 4096 11월 23 20:42 /home/researcher_a
drwxr-x--- 2 researcher_b researcher_b 4096 11월 23 20:42 /home/researcher_b

$ ls -ld /srv/models
drwxrwsr-x 2 beck llm-admins 4096 11월 23 20:43 /srv/models

$ cd /srv/models/Qwen3-8B
$ jq -r '.weight_map[]' model.safetensors.index.json | sort -u > /tmp/expected.txt
$ ls *.safetensors | sort > /tmp/actual.txt
$ diff /tmp/expected.txt /tmp/actual.txt && echo "가중치 파일 일치"
가중치 파일 일치
$ cat /tmp/actual.txt
model-00001-of-00005.safetensors
model-00002-of-00005.safetensors
model-00003-of-00005.safetensors
model-00004-of-00005.safetensors
model-00005-of-00005.safetensors
$ ls config.json tokenizer.json generation_config.json
config.json
generation_config.json
tokenizer.json
$ du -sh .
16G	.

$ ip -4 -brief addr | grep -v '^lo'
enp6s0           UP             172.30.1.44/24 
br-e5378fa6218e  UP             172.18.0.1/16 
docker0          DOWN           172.17.0.1/16 
```

## 3단계 SSH 키 접속과 비밀번호 차단

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| ssh 서비스 | active | ssh active, ssh.socket active | 통과 |
| 22번 포트 | LISTEN | 0.0.0.0:22, [::]:22 LISTEN | 통과 |
| passwordauthentication | no | no (sshd -T, 10-hardening.conf) | 통과 |
| kbdinteractiveauthentication | no | no | 통과 |
| permitrootlogin | no | no | 통과 |
| allowgroups | llm-admins llm-users | llm-admins, llm-users (sshd -T는 그룹마다 한 줄씩 출력) | 통과 |
| maxauthtries | 3 | 3 | 통과 |
| localhost 비밀번호 로그인 | Permission denied (publickey) | beck@localhost: Permission denied (publickey). 종료 코드 255 | 통과 |
| 노트북 키 로그인 | key-login-ok | key-login-ok | 통과 |
| 노트북 비밀번호 로그인 | Permission denied (publickey) | beck@172.30.1.44: Permission denied (publickey). | 통과 |
| researcher_a docker 접근 | permission denied | permission denied ... docker.sock | 통과 |
| 노트북 키 로그인 계정 수 | 4 (beck, admin, researcher_a, researcher_b) | 4 (whoami 출력 4개) | 통과 |
| sshd 로그 Accepted publickey 계정 수 | 4 | 4 (beck 3회, researcher_a 2회, admin 1회, researcher_b 1회) | 통과 |

서버 호스트 키 지문(ED25519): SHA256:G9IN8lsHyGiOmvHi2ok1LJk0X8omyyiB4YlXKc+PUB8

### 메모
- 노트북에서 scp할 때 Windows 한국어 입력기 때문에 비밀번호 입력이 실패했다. 영어 입력기로 바꾸고 beck 비밀번호를 재설정해서 해결했다.
- sshd 로그의 Failed password 7건(21:48~22:45)은 10-hardening.conf 작성 시각(23:08) 이전 기록이다.
- 로그의 원격 포트 번호는 `port *`로 지웠다.

### 원본 출력

```text
$ systemctl is-active ssh ssh.socket
active
active
(exit=0)

$ ss -tlnp 2>/dev/null | grep ':22 '
LISTEN 0      4096         0.0.0.0:22         0.0.0.0:*                                       
LISTEN 0      4096            [::]:22            [::]:*                                       
(exit=0)

$ ls -l /etc/ssh/sshd_config.d/
합계 4
-rw-r--r-- 1 root root 208 11월 23 23:08 10-hardening.conf
(exit=0)

$ cat /etc/ssh/sshd_config.d/10-hardening.conf
# 키 인증만 허용, root 차단, 두 그룹만 접속
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
AllowGroups llm-admins llm-users
MaxAuthTries 3
(exit=0)

$ ssh -o BatchMode=yes -o PubkeyAuthentication=no -o PreferredAuthentications=password -o StrictHostKeyChecking=accept-new beck@localhost true
beck@localhost: Permission denied (publickey).
(exit=255)

$ journalctl -u ssh --since "2 hours ago" --no-pager | grep -Ei "Accepted publickey|Failed|Disconnected" | tail -20
11월 23 21:48:10 beck sshd[163232]: Failed password for beck from 172.30.1.34 port * ssh2
11월 23 21:48:14 beck sshd[163232]: Failed password for beck from 172.30.1.34 port * ssh2
11월 23 21:49:44 beck sshd[163654]: Failed password for beck from 172.30.1.34 port * ssh2
11월 23 21:49:48 beck sshd[163654]: Failed password for beck from 172.30.1.34 port * ssh2
11월 23 21:49:52 beck sshd[163654]: Failed password for beck from 172.30.1.34 port * ssh2
11월 23 22:40:25 beck sshd[180261]: Failed password for beck from 172.30.1.34 port * ssh2
11월 23 22:45:44 beck sshd[182874]: Failed password for beck from 127.0.0.1 port * ssh2
11월 23 22:52:12 beck sshd[186253]: Accepted publickey for beck from 172.30.1.34 port * ssh2: ED25519 SHA256:of0UT7dZcYDT9794z76I/2kERfPne7tHdUpV+J6It0M
11월 23 22:52:18 beck sshd[186324]: Accepted publickey for admin from 172.30.1.34 port * ssh2: ED25519 SHA256:88aWABPukuqrSlI8228BzsCCZmg0PRB8La8ewEwBT5g
11월 23 22:52:18 beck sshd[186631]: Accepted publickey for researcher_a from 172.30.1.34 port * ssh2: ED25519 SHA256:7cmJSpM20BoppPTdlnuV78j6EKtuEeLOTsv9/s7c5Ig
11월 23 22:55:26 beck sshd[188481]: Accepted publickey for researcher_b from 172.30.1.34 port * ssh2: ED25519 SHA256:ewdNGlCy8BZ6/prq9pOWlIGMrRShBBJzmyKASQBReSA
11월 23 23:10:53 beck sshd[193405]: Accepted publickey for beck from 172.30.1.34 port * ssh2: ED25519 SHA256:of0UT7dZcYDT9794z76I/2kERfPne7tHdUpV+J6It0M
11월 23 23:16:52 beck sshd[195738]: Accepted publickey for beck from 172.30.1.34 port * ssh2: ED25519 SHA256:of0UT7dZcYDT9794z76I/2kERfPne7tHdUpV+J6It0M
11월 23 23:17:43 beck sshd[196201]: Accepted publickey for researcher_a from 172.30.1.34 port * ssh2: ED25519 SHA256:7cmJSpM20BoppPTdlnuV78j6EKtuEeLOTsv9/s7c5Ig

$ ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
256 SHA256:G9IN8lsHyGiOmvHi2ok1LJk0X8omyyiB4YlXKc+PUB8 root@beck (ED25519)

[붙여넣기: 사용자 제공 노트북·sudo 출력]
(⑤ sudo sshd -T 출력)
maxauthtries 3
permitrootlogin no
passwordauthentication no
kbdinteractiveauthentication no
allowgroups llm-admins
allowgroups llm-users

(④ 노트북 키 로그인 whoami)
beck
admin   (패스프레이즈 입력 후)
researcher_a
researcher_b

(⑥ 노트북 출력)
PS> ssh llm-me "echo key-login-ok"
key-login-ok
PS> ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password llm-me
beck@172.30.1.44: Permission denied (publickey).
PS> ssh llm-researcher-a "groups; docker ps"
researcher_a users llm-users
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

## 4단계 Docker GPU 런타임

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| docker 서버 버전 | 설치됨(29.x) | 29.9.3 (apt 후보 29.10.0) | 통과 |
| docker compose | v2 이상 | v5.7.0 | 통과 |
| nvidia-container-toolkit | 설치됨 | 1.20.2-1 (nvidia-ctk 1.20.2) | 통과 |
| daemon.json nvidia 런타임 | 있음 | runtimes.nvidia.path = nvidia-container-runtime | 통과 |
| docker info Runtimes | nvidia 포함 | io.containerd.runc.v2, nvidia, runc | 통과 |
| 컨테이너 GPU 이름 | NVIDIA GeForce RTX 5090 | NVIDIA GeForce RTX 5090 | 통과 |
| 컨테이너 드라이버 | 호스트와 같음(580.178.04) | 580.178.04, CUDA Version 13.0 | 통과 |
| 컨테이너 GPU 메모리 | 32607 MiB | 32607 MiB | 통과 |
| docker.sock 권한 | root:docker, srw-rw---- | srw-rw---- root docker | 통과 |

메모
- 테스트 이미지 nvidia/cuda:12.8.1-base-ubuntu24.04를 새로 받았다.
- `nvidia-smi | head -4`의 "write /dev/stdout: broken pipe"는 head가 4줄 뒤 파이프를 닫아서 생긴 메시지다. 오류가 아니다.
- vLLM 이미지 미리 받기(8단계)는 사용자 승인 전이라 하지 않았다.

### 원본 출력

```text
$ id -nG
beck adm cdrom sudo dip plugdev users lpadmin docker llm-admins
(exit=0)

$ docker version --format '{{.Server.Version}}'
29.9.3
(exit=0)

$ docker compose version
Docker Compose version v5.7.0
(exit=0)

$ nvidia-ctk --version
NVIDIA Container Toolkit CLI version 1.20.2
commit: adbd28c39b60f8eb7e03115b5ac61e58703f0ce7
(exit=0)

$ dpkg -l nvidia-container-toolkit | tail -1
ii  nvidia-container-toolkit 1.20.2-1     amd64        NVIDIA Container toolkit
(exit=0)

$ apt-cache policy docker-ce | head -3
docker-ce:
  설치: 5:29.9.3-1~ubuntu.24.04~noble
  후보: 5:29.10.0-1~ubuntu.24.04~noble
(exit=0)

$ cat /etc/docker/daemon.json
{
    "runtimes": {
        "nvidia": {
            "args": [],
            "path": "nvidia-container-runtime"
        }
    }
}(exit=0)

$ docker info --format '{{json .Runtimes}}' | jq 'keys'
[
  "io.containerd.runc.v2",
  "nvidia",
  "runc"
]
(exit=0)

$ docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
name, driver_version, memory.total [MiB]
NVIDIA GeForce RTX 5090, 580.178.04, 32607 MiB
(exit=0)

$ docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi | head -4
Tue Nov 24 01:53:36 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.178.04             Driver Version: 580.178.04     CUDA Version: 13.0     |
+-----------------------------------------+------------------------+----------------------+
write /dev/stdout: broken pipe
(exit=0)

$ ls -l /var/run/docker.sock
srw-rw---- 1 root docker 0 11월 24 10:32 /var/run/docker.sock
(exit=0)

```

이미지 미리 받기: `docker image ls vllm/vllm-openai` → v0.33.0 35.4GB (10:54:39 시작 → 10:58:15 로그 마지막 기록, 약 4분. digest sha256:d825baf9ce4b1b6bfc5ecc7b79880c7e6748c65a72d697ce3d47607aafa84c6e)

## 6단계 설정 파일

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 호스트 4000 포트 | 사용 안 함 | 사용 안 함 (8080만 LISTEN, frappe) | 통과 |
| 컨테이너 이름 충돌 | vllm, litellm, litellm-db 없음 | 이름 충돌 없음 | 통과 |
| .env 권한(600) | 600 | 600 beck | 통과 |
| .env 값 3개 | 3 | 3 (LITELLM_MASTER_KEY, LITELLM_SALT_KEY, POSTGRES_PASSWORD) | 통과 |
| .env Git 제외 | git check-ignore → .env | .env | 통과 |
| compose 문법 | config --quiet 성공 | compose 문법 OK | 통과 |
| 서비스 수(3) | vllm, db, litellm | db, vllm, litellm | 통과 |
| 모델 경로 | /srv/models/Qwen3-8B/config.json 존재 | 존재 | 통과 |
| vLLM 이미지 | v0.33.0 있음 | v0.33.0 35.4GB | 통과 |
| LiteLLM 이미지 digest | 받기 성공, digest 조회 | sha256:ef798594ca3db8d81bad2e1439f536f49b71fe095ee9f20416f5e149b4e22035 (1.9GB). postgres:16.16 667MB | 통과 |

메모
- 이 스택이 호스트에 여는 포트는 127.0.0.1:4000 하나다. 8000(vLLM), 5432(Postgres)는 backend 내부망에서만 쓴다.
- 참고 포트: 8080은 frappe_docker-frontend-1이 0.0.0.0:8080으로 사용 중이다. 2~3일차에 8080을 쓰려면 다른 포트가 필요하다. 9090, 3000은 비어 있다.
- .env.example에는 LITELLM_MASTER_KEY=, POSTGRES_PASSWORD=가 이미 있어 LITELLM_SALT_KEY= 한 줄만 끝에 추가했다.
- .env 값은 openssl rand로 만들었고 이 기록에는 넣지 않았다.
- 컨테이너는 만들지 않았다. 작업 전후 `docker ps -aq` 15개로 같다.

참고: 기존 컨테이너

```text
$ ss -tlnH | awk '{print $4}' | grep -E ':(4000|5432|8000|8080|9090|3000)$'
0.0.0.0:8080
[::]:8080
(exit=0)

$ docker ps --format '{{.Names}}\t{{.Ports}}'
frappe_docker-frontend-1	0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
frappe_docker-websocket-1	
frappe_docker-queue-short-1	
frappe_docker-queue-long-1	
frappe_docker-backend-1	
frappe_docker-scheduler-1	
frappe_docker-redis-cache-1	6379/tcp
frappe_docker-redis-queue-1	6379/tcp
frappe_docker-db-1	3306/tcp
(exit=0)

$ docker ps -a --format '{{.Names}}' | grep -xE 'vllm|litellm|litellm-db' || echo '이름 충돌 없음'
이름 충돌 없음
(exit=0)

$ docker compose ls
NAME                STATUS              CONFIG FILES
frappe_docker       running(9)          /home/beck/바탕화면/epr/frappe_docker/pwd.yml,/home/beck/바탕화면/epr/erpnext-ops-agent/infra/pwd.override.yml
(exit=0)

```

### 원본 출력

```text
$ stat -c '%a %U' .env
600 beck
(exit=0)

$ grep -cE '^(LITELLM_MASTER_KEY=sk-|LITELLM_SALT_KEY=sk-|POSTGRES_PASSWORD=.+)' .env
3
(exit=0)

$ git check-ignore .env
.env
(exit=0)

$ docker compose config --quiet && echo 'compose 문법 OK'
compose 문법 OK
(exit=0)

$ docker compose config --services
db
vllm
litellm
(exit=0)

$ ls /srv/models/Qwen3-8B/config.json
/srv/models/Qwen3-8B/config.json
(exit=0)

$ docker image ls vllm/vllm-openai --format '{{.Tag}} {{.Size}}'
v0.33.0 35.4GB
(exit=0)

$ docker compose pull db litellm
(exit=0 확인, 레이어 진행 줄은 생략)

$ docker image inspect ghcr.io/berriai/litellm:main-stable --format '{{index .RepoDigests 0}}'
ghcr.io/berriai/litellm@sha256:ef798594ca3db8d81bad2e1439f536f49b71fe095ee9f20416f5e149b4e22035
(exit=0)

$ docker image ls --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep -E '^(postgres:16.16|ghcr.io/berriai/litellm:main-stable) '
ghcr.io/berriai/litellm:main-stable 1.9GB
postgres:16.16 667MB
(exit=0)

```

## 7단계 기동과 검증

| 항목 | 기준 | 추정 | 실측 | 판정 |
|---|---|---|---|---|
| LiteLLM digest 고정 | sha256 있음 | - | ghcr.io/berriai/litellm@sha256:ef798594ca3db8d81bad2e1439f536f49b71fe095ee9f20416f5e149b4e22035 | 통과 |
| chrome·steam | 없음 | - | chrome 켜짐(695 MiB), 여유 기준 통과로 진행 | 참고 |
| 기동 전 GPU 여유 | 28000 MiB 이상 | - | 31066 MiB (점검 시), 31095 MiB (기동 직전) | 통과 |
| vllm 상태 | healthy | - | Up (healthy), 재시작 0회 | 통과 |
| litellm-db 상태 | healthy | - | Up (healthy), 재시작 0회 | 통과 |
| litellm 상태 | Up | - | Up, 재시작 0회 | 통과 |
| 기동 소요 | 2~5분 | 2~5분 | 약 2.9분 (12:54:10 → 12:57:05). vLLM 엔진 초기화 132.67 s | 통과 |
| GPU KV cache 토큰 | 약 70,000 | 약 70,000 | 69,120 | 통과 |
| 최대 동시 요청(8192 길이) | 약 8 | 약 8 | 8.44 | 통과 |
| 기동 후 GPU 사용 | 27~28 GB | 27~28 GB | 28090 MiB (27.4 GiB, 데스크톱 약 1.5 GiB 포함) | 통과 |
| /v1/models | qwen3-8b | - | qwen3-8b | 통과 |
| 첫 응답 | HTTP 200, 한국어 | - | HTTP 200, 한국어 한 문장 | 통과 |
| 첫 응답 지연 | 기록만 | - | 0.73 s (prompt 27, completion 50, total 77 토큰) | 기록만 |
| 4000 포트 | 127.0.0.1만 | - | 127.0.0.1:4000 LISTEN | 통과 |
| vllm 호스트 포트 | 없음 | - | docker port vllm 출력 없음 | 통과 |

추정과 실측이 20% 넘게 차이 나는 항목은 없다. KV cache 1.3%, 동시 요청 5.5%, GPU 사용은 27~28 범위 안이다.

메모
- 사용자 결정으로 chrome을 켠 채 진행했다. chrome 판정은 참고로만 기록했고, GPU 여유 28000 MiB 기준만 적용했다.
- 답변 앞에 빈 `<think>\n\n</think>` 블록이 붙는다. vLLM에 reasoning parser를 설정하지 않아서다.
- vLLM 로그 안내: CUDA graph 메모리 프로파일링 때문에 0.85는 예전 기준 0.8362에 해당한다. 같은 KV cache 크기를 원하면 0.8638을 쓰라고 안내한다. 설정은 바꾸지 않았다.
- 모델 가중치 로딩 15.27 GiB, KV cache 9.49 GiB, CUDA graph 캡처 56 s + 54 s.

참고: 기존 컨테이너

```text
frappe_docker: 전체 11, 실행 9, 정지 2
(없음): 전체 4, 실행 0, 정지 4
llm-platform: 기동 전 0개

frappe 외 컨테이너 (이름, 이미지, 상태):
great_faraday	hello-world	Exited (0) 2 weeks ago
lucid_blackburn	hello-world	Exited (0) 2 weeks ago
busy_clarke	hello-world	Exited (0) 2 weeks ago
hardcore_meninsky	hello-world	Exited (0) 2 weeks ago
```

### 원본 출력

```text
$ date +%T
12:54:10
$ docker compose up -d
 Network llm-platform_backend Creating 
 Volume llm-platform_pgdata Creating 
 Volume llm-platform_pgdata Creating 
 Network llm-platform_backend Creating 
 Volume llm-platform_pgdata Created 
 Volume llm-platform_pgdata Created 
 Network llm-platform_backend Created 
 Network llm-platform_backend Created 
 Container vllm Creating 
 Container litellm-db Creating 
 Container litellm-db Created 
 Container vllm Created 
 Container litellm Creating 
 Container litellm Created 
 Container vllm Starting 
 Container litellm-db Starting 
 Container vllm Started 
 Container vllm Waiting 
 Container litellm-db Started 
 Container litellm-db Waiting 
 Container litellm-db Healthy 
 Container vllm Healthy 
 Container litellm Starting 
 Container litellm Started 
(exit=0)

[12:57:05]
litellm	Up 6 seconds
litellm-db	Up 2 minutes (healthy)
vllm	Up 2 minutes (healthy)
완료 12:57:05

$ docker compose logs vllm | grep -iE "KV cache|maximum concurrency|Application startup complete" | tail -5
vllm  | (EngineCore pid=216) INFO 11-24 03:56:00 [gpu_worker.py:787] CUDA graph memory profiling is enabled (default since v0.21.0). The current --gpu-memory-utilization=0.8500 is equivalent to --gpu-memory-utilization=0.8362 without CUDA graph memory profiling. To maintain the same effective KV cache size as before, increase --gpu-memory-utilization to 0.8638. To disable, set VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=0.
vllm  | (EngineCore pid=216) INFO 11-24 03:56:00 [kv_cache_utils.py:1147] GPU KV cache size: 69,120 tokens, Maximum concurrency for 8,192 tokens per request: 8.44x
vllm  | (EngineCore pid=216) INFO 11-24 03:56:55 [gpu_worker.py:1066] Free memory on device (29.34/31.32 GiB) on startup. Desired GPU memory utilization is (0.85, 26.63 GiB). Actual usage is 15.51 GiB for consumed memory (weights + non-torch), 1.62 GiB for peak activation, and 0.18 GiB for CUDAGraph memory. Replace gpu_memory_utilization config with `--kv-cache-memory=9844615680` (9.17 GiB) to fit into requested memory, or `--kv-cache-memory=12764752384` (11.89 GiB) to fully utilize gpu memory. Current kv cache memory in use is 9.49 GiB.
vllm  | (EngineCore pid=216) INFO 11-24 03:56:56 [core.py:405] init engine (profile, create kv cache, warmup model) took 132.67 s (compilation: 16.68 s)
vllm  | INFO:     Application startup complete.
$ nvidia-smi --query-gpu=memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader
28090 MiB, 32607 MiB, 39, 43.78 W

$ curl -s http://127.0.0.1:4000/v1/models -H "Authorization: Bearer $K" | jq -r '.data[].id'
qwen3-8b

$ curl -s -o /tmp/day1_chat.json -w "HTTP %{http_code} / %{time_total}s\n" http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer $K" ... (서울의 수도 기능을 한 문장으로 설명해줘. /no_think, max_tokens 128)
HTTP 200 / 0.725611s

$ jq '{answer: .choices[0].message.content, usage: .usage}' /tmp/day1_chat.json
{
  "answer": "<think>\n\n</think>\n\n서울은 대한민국의 수도로서 정부, 의회, 주요 정책 결정 기관이 위치해 있으며, 국가의 정치, 경제, 문화적 중심지로 기능하고 있습니다.",
  "usage": {
    "completion_tokens": 50,
    "prompt_tokens": 27,
    "total_tokens": 77
  }
}

$ ss -tlnH | grep ':4000 '
LISTEN 0      4096       127.0.0.1:4000  0.0.0.0:*

$ docker port vllm || echo "vllm 호스트 포트 없음"
(docker port vllm은 출력 없이 종료 코드 0으로 끝나 echo가 실행되지 않음)
```
