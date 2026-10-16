import html
import json
import random
import re
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timezone


class FourChanSource:
    """Sample public replies from selected 4chan boards using the read-only JSON API."""

    def __init__(
        self,
        api_base: str = "https://a.4cdn.org",
        poll_seconds: float = 5.0,
        request_lock=None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.poll_seconds = max(1.0, poll_seconds)
        self.request_lock = request_lock

        self.boards = ["v", "g", "pol", "int", "lgbt"]
        self.board_names = {
            "v": "Video Games",
            "g": "Technology",
            "pol": "Politically Incorrect",
            "int": "International",
            "lgbt": "LGBT",
        }
        self.board_index = 0
        self.pending_thread: dict | None = None

        self.queue: deque[dict] = deque(maxlen=300)
        self.recent_thread_ids: deque[str] = deque(maxlen=150)

        self.max_seen_ids = 3000
        self.seen_ids: set[str] = set()
        self.seen_id_order: deque[str] = deque()

    def _request_json(self, url: str):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "ChatterFeed/2.2 (non-commercial art project)",
            },
        )

        if self.request_lock is None:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))

        with self.request_lock:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _plain_text(value: str) -> str:
        value = value or ""
        value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
        value = re.sub(r"<[^>]+>", "", value)
        value = html.unescape(value)
        lines = [line.strip() for line in value.splitlines()]
        return "\n".join(line for line in lines if line).strip()

    @staticmethod
    def _contains_non_latin_script(text: str) -> bool:
        patterns = [
            r"[\u3040-\u30ff]",
            r"[\u3400-\u4dbf\u4e00-\u9fff]",
            r"[\uac00-\ud7af]",
            r"[\u0400-\u04ff]",
            r"[\u0590-\u05ff]",
            r"[\u0600-\u06ff]",
            r"[\u0900-\u097f]",
            r"[\u0e00-\u0e7f]",
        ]
        return sum(len(re.findall(pattern, text)) for pattern in patterns) >= 4

    @classmethod
    def _should_ignore(cls, text: str) -> bool:
        if not text or len(text) >= 1000:
            return True
        if cls._contains_non_latin_script(text):
            return True
        return len(re.findall(r"https?://\S+", text, flags=re.IGNORECASE)) > 2

    def _remember_seen(self, post_id: str) -> None:
        if post_id in self.seen_ids:
            return

        self.seen_ids.add(post_id)
        self.seen_id_order.append(post_id)

        while len(self.seen_id_order) > self.max_seen_ids:
            expired = self.seen_id_order.popleft()
            self.seen_ids.discard(expired)

    def _fetch_catalog(self, board: str) -> list[dict]:
        url = f"{self.api_base}/{board}/catalog.json"
        data = self._request_json(url)
        return data if isinstance(data, list) else []

    def _fetch_thread(self, board: str, thread_id: int) -> dict:
        url = f"{self.api_base}/{board}/thread/{thread_id}.json"
        data = self._request_json(url)
        return data if isinstance(data, dict) else {}

    def _choose_thread(self, board: str, catalog: list[dict]) -> None:
        candidates = []

        for page in catalog:
            for thread in page.get("threads", []):
                thread_id = thread.get("no")
                replies = int(thread.get("replies", 0) or 0)

                if not thread_id or replies <= 0:
                    continue

                key = f"{board}:{thread_id}"
                if key in self.recent_thread_ids:
                    continue

                candidates.append(thread)

        if not candidates:
            self.pending_thread = None
            return

        # Favor active threads while retaining some randomness.
        candidates.sort(
            key=lambda thread: int(thread.get("last_modified", 0) or 0),
            reverse=True,
        )
        active_pool = candidates[: min(30, len(candidates))]
        chosen = random.choice(active_pool)

        thread_id = int(chosen["no"])
        key = f"{board}:{thread_id}"
        self.recent_thread_ids.append(key)
        self.pending_thread = {
            "board": board,
            "thread_id": thread_id,
            "subject": f"/{board}/ {self.board_names.get(board, board)}",
        }

    def _queue_replies(self, subject: str, data: dict) -> None:
        posts = data.get("posts", [])
        if not isinstance(posts, list) or len(posts) <= 1:
            return

        eligible = []
        for post in posts[1:]:
            post_id = post.get("no")
            if not post_id:
                continue

            key = f"{subject}:{post_id}"
            if key in self.seen_ids:
                continue

            text = self._plain_text(str(post.get("com", "")))
            if self._should_ignore(text):
                continue

            eligible.append((post, key, text))

        if not eligible:
            return

        sample_size = min(len(eligible), random.randint(2, 4))
        for post, key, text in random.sample(eligible, sample_size):
            self._remember_seen(key)

            unix_time = int(post.get("time", 0) or 0)
            if unix_time:
                timestamp = datetime.fromtimestamp(
                    unix_time,
                    tz=timezone.utc,
                ).isoformat(timespec="seconds")
            else:
                timestamp = datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                )

            self.queue.append(
                {
                    "source": "4chan",
                    "subject": subject,
                    "timestamp": timestamp,
                    "text": text,
                }
            )

    def stream(self):
        fetch_thread_next = False

        while True:
            try:
                if fetch_thread_next and self.pending_thread:
                    data = self._fetch_thread(
                        self.pending_thread["board"],
                        self.pending_thread["thread_id"],
                    )
                    self._queue_replies(
                        self.pending_thread["subject"],
                        data,
                    )
                    self.pending_thread = None
                    fetch_thread_next = False

                else:
                    board = self.boards[self.board_index]
                    catalog = self._fetch_catalog(board)
                    self._choose_thread(board, catalog)

                    self.board_index = (
                        self.board_index + 1
                    ) % len(self.boards)

                    fetch_thread_next = self.pending_thread is not None

            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                json.JSONDecodeError,
            ) as error:
                print(f"[4chan connection error] {error}")
                self.pending_thread = None
                fetch_thread_next = False

            if self.queue:
                yield self.queue.popleft()

            time.sleep(self.poll_seconds)
