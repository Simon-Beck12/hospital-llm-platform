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
