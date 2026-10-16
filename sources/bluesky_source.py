import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime


class BlueskySource:
    """Search public Bluesky posts and sample replies from active threads."""

    def __init__(
        self,
        api_base: str = "https://public.api.bsky.app",
        search_base: str = "https://api.bsky.app",
        poll_seconds: float = 5.0,
        request_lock=None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.search_base = search_base.rstrip("/")
        self.poll_seconds = poll_seconds
        self.request_lock = request_lock

        self.topics = [
            "politics",
            "humanrights",
            "climate",
            "lgbtq",
            "culture",
            "israel",
            "palestine",
            "christianity",
            "jewish",
            "feminism",
            "religion",
            "life",
            "thoughts",
            "chat",
            "sex",
            "homosexual",
            "transexual",
            "rightwing",
        ]

        self.topic_index = 0
        self.pending_thread: dict | None = None
        self.recent_thread_uris: deque[str] = deque(maxlen=100)
        self.queue: deque[dict] = deque(maxlen=300)

        self.max_seen_uris = 2000
        self.seen_uris: set[str] = set()
        self.seen_uri_order: deque[str] = deque()

    def _request_json(self, url: str):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "ChatterFeed/2.1 (non-commercial art project)",
            },
        )

        if self.request_lock is None:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))

        with self.request_lock:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))

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
        return sum(len(re.findall(p, text)) for p in patterns) >= 4

    @classmethod
    def _should_ignore(cls, text: str) -> bool:
        if not text or len(text) >= 1000:
            return True
        if cls._contains_non_latin_script(text):
            return True
        return len(re.findall(r"https?://\S+", text, flags=re.IGNORECASE)) > 2

    def _remember_seen(self, uri: str) -> None:
        if uri in self.seen_uris:
            return
        self.seen_uris.add(uri)
        self.seen_uri_order.append(uri)

        while len(self.seen_uri_order) > self.max_seen_uris:
            expired = self.seen_uri_order.popleft()
            self.seen_uris.discard(expired)

    def _search_posts(self, topic: str) -> list[dict]:
        query = urllib.parse.urlencode(
            {
                "q": topic,
                "limit": "25",
                "sort": "latest",
            }
        )
        url = (
            f"{self.search_base}/xrpc/"
            f"app.bsky.feed.searchPosts?{query}"
        )
        data = self._request_json(url)
        posts = data.get("posts", []) if isinstance(data, dict) else []
        return posts if isinstance(posts, list) else []

    def _fetch_thread(self, uri: str) -> dict:
        query = urllib.parse.urlencode(
            {
                "uri": uri,
                "depth": "6",
                "parentHeight": "0",
            }
        )
        url = (
            f"{self.api_base}/xrpc/"
            f"app.bsky.feed.getPostThread?{query}"
        )
        data = self._request_json(url)
        return data if isinstance(data, dict) else {}

    def _choose_thread_candidate(self, topic: str, posts: list[dict]) -> None:
        candidates = []

        for post in posts:
            if int(post.get("replyCount", 0) or 0) <= 0:
                continue

            uri = post.get("uri")
            if not uri or uri in self.recent_thread_uris:
                continue

            record = post.get("record", {})
            langs = record.get("langs", [])
            if langs and "en" not in [str(lang).lower() for lang in langs]:
                continue

            candidates.append(post)

        if not candidates:
            self.pending_thread = None
            return

        chosen = random.choice(candidates)
        uri = chosen["uri"]
        self.recent_thread_uris.append(uri)
        self.pending_thread = {
            "uri": uri,
            "subject": f"#{topic}",
        }

    def _collect_reply_nodes(self, node: dict, output: list[dict]) -> None:
        replies = node.get("replies", [])
        if not isinstance(replies, list):
            return

        for reply in replies:
            if not isinstance(reply, dict):
                continue

            post = reply.get("post")
            if isinstance(post, dict):
                output.append(post)

            self._collect_reply_nodes(reply, output)

    def _queue_thread_replies(self, subject: str, data: dict) -> None:
        root = data.get("thread")
        if not isinstance(root, dict):
            return

        reply_posts: list[dict] = []
        self._collect_reply_nodes(root, reply_posts)

        eligible = []
        for post in reply_posts:
            uri = post.get("uri")
            if not uri or uri in self.seen_uris:
                continue

            record = post.get("record", {})
            text = str(record.get("text", "")).strip()
            langs = record.get("langs", [])

            if langs and "en" not in [str(lang).lower() for lang in langs]:
                continue
            if self._should_ignore(text):
                continue

            eligible.append(post)

        if not eligible:
            return

        sample_size = min(len(eligible), random.randint(2, 4))

        for post in random.sample(eligible, sample_size):
            uri = post["uri"]
            self._remember_seen(uri)

            record = post.get("record", {})
            text = str(record.get("text", "")).strip()
            created_at = record.get(
                "createdAt",
                datetime.now().isoformat(timespec="seconds"),
            )

            self.queue.append(
                {
                    "source": "bsky.app",
                    "subject": subject,
                    "timestamp": created_at,
                    "text": text,
                }
            )

    def stream(self):
        fetch_thread_next = False

        while True:
            try:
                if fetch_thread_next and self.pending_thread:
                    data = self._fetch_thread(self.pending_thread["uri"])
                    self._queue_thread_replies(
                        self.pending_thread["subject"],
                        data,
                    )
                    self.pending_thread = None
                    fetch_thread_next = False

                else:
                    topic = self.topics[self.topic_index]
                    posts = self._search_posts(topic)
                    self._choose_thread_candidate(topic, posts)

                    self.topic_index = (
                        self.topic_index + 1
                    ) % len(self.topics)

                    fetch_thread_next = self.pending_thread is not None

            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                json.JSONDecodeError,
            ) as error:
                print(f"[Bluesky connection error] {error}")
                self.pending_thread = None
                fetch_thread_next = False

            if self.queue:
                yield self.queue.popleft()

            time.sleep(self.poll_seconds)
