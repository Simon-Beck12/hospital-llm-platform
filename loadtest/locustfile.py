"""게이트웨이 부하 테스트(Locust).

키는 LOADTEST_KEY_FILE(기본 ~/llm-keys/loadtest.key)에서 시작 시 한 번 읽는다. 키는 출력하지 않는다.
실행 예:
  uv run locust -f loadtest/locustfile.py --headless --host http://127.0.0.1:18080 \
    -u 8 -r 4 -t 3m --csv loadtest/results/u8 --only-summary
"""

import os
import random
from pathlib import Path

from locust import HttpUser, between, task

KEY_FILE = Path(os.environ.get("LOADTEST_KEY_FILE", "~/llm-keys/loadtest.key")).expanduser()
API_KEY = KEY_FILE.read_text(encoding="utf-8").strip()

TOPICS = [
    "광합성",
    "블록체인",
    "기후 변화",
    "인공지능",
    "백신의 원리",
    "조선 왕조",
    "태양계",
    "반도체",
    "커피의 역사",
    "지진",
    "DNA",
    "인터넷",
    "올림픽",
    "화산",
    "전기차",
    "한글 창제",
    "양자역학",
    "미세먼지",
    "고래",
    "피라미드",
]


class GatewayUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        self.client.headers.update(
            {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        )

    @task
    def chat(self) -> None:
        topic = random.choice(TOPICS)
        body = {
            "model": "qwen3-8b",
            "messages": [
                {
                    "role": "user",
                    "content": f"다음 주제를 200자 안팎으로 설명해줘: {topic} /no_think",
                }
            ],
            "max_tokens": 128,
        }
        with self.client.post(
            "/v1/chat/completions", json=body, name="/v1/chat/completions", catch_response=True
        ) as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure(f"HTTP {res.status_code}")
