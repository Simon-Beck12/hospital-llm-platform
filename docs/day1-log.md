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
