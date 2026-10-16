import html
import random
import re
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser


class _PostTextParser(HTMLParser):
    """Extract likely post-message containers from 8kun/OpenIB HTML."""

    MESSAGE_CLASSES = {
        "divMessage",
        "message",
        "postMessage",
        "postBody",
        "body",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.capture_depth = None
        self.buffer: list[str] = []
        self.messages: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.depth += 1
        attrs_dict = dict(attrs)

        if self.capture_depth is None:
            classes = set(attrs_dict.get("class", "").split())
            if classes & self.MESSAGE_CLASSES:
                self.capture_depth = self.depth
                self.buffer = []

        if self.capture_depth is not None and tag in {"br", "p", "div"}:
            self.buffer.append("\n")

    def handle_startendtag(self, tag, attrs):
        if self.capture_depth is not None and tag == "br":
            self.buffer.append("\n")

    def handle_data(self, data):
        if self.capture_depth is not None:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if self.capture_depth is not None and self.depth == self.capture_depth:
            text = " ".join("".join(self.buffer).split())
            if text:
                self.messages.append(text)
            self.capture_depth = None
            self.buffer = []

        self.depth = max(0, self.depth - 1)


class EightKunSource:
    """Sample public /qresearch/ discussion from 8kun HTML pages."""

    def __init__(
        self,
        base_url: str = "https://8kun.top",
        poll_seconds: float = 5.0,
        request_lock=None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.poll_seconds = poll_seconds
        self.request_lock = request_lock

        self.board = "qresearch"
        self.queue: deque[dict] = deque(maxlen=300)
        self.recent_thread_ids: deque[str] = deque(maxlen=100)

        self.max_seen_texts = 2000
        self.seen_texts: set[str] = set()
        self.seen_text_order: deque[str] = deque()

    def _request_text(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": "ChatterFeed/2.3 (non-commercial art project)",
            },
        )

        if self.request_lock is None:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.read().decode("utf-8", errors="replace")

        with self.request_lock:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _thread_ids(page_html: str) -> list[str]:
        patterns = [
            r'href=["\'](?:https?://[^"\']+)?/qresearch/res/(\d+)\.html',
            r'href=["\']res/(\d+)\.html',
        ]

        ids = []
        seen = set()
        for pattern in patterns:
            for thread_id in re.findall(pattern, page_html, flags=re.IGNORECASE):
                if thread_id not in seen:
                    seen.add(thread_id)
                    ids.append(thread_id)
        return ids

    @staticmethod
    def _extract_messages(page_html: str) -> list[str]:
        parser = _PostTextParser()
        parser.feed(page_html)

        messages = []
        for message in parser.messages:
            text = html.unescape(message).strip()
            text = re.sub(r"\s+", " ", text)

            if not text or len(text) >= 1000:
                continue

            if len(re.findall(r"https?://\S+", text, flags=re.IGNORECASE)) > 2:
                continue

            messages.append(text)

        return messages

    def _remember_text(self, text: str) -> None:
        key = text[:500]
        if key in self.seen_texts:
            return

        self.seen_texts.add(key)
        self.seen_text_order.append(key)

        while len(self.seen_text_order) > self.max_seen_texts:
            expired = self.seen_text_order.popleft()
            self.seen_texts.discard(expired)

    def _choose_thread(self, index_html: str) -> str | None:
        thread_ids = [
            thread_id
            for thread_id in self._thread_ids(index_html)
            if thread_id not in self.recent_thread_ids
        ]

        if not thread_ids:
            return None

        # The board index tends to list active threads first. Sample from the
        # first group rather than always taking the same current bread.
        active_pool = thread_ids[: min(20, len(thread_ids))]
        chosen = random.choice(active_pool)
        self.recent_thread_ids.append(chosen)
        return chosen

    def _queue_thread_messages(self, page_html: str) -> None:
        messages = [
            text
            for text in self._extract_messages(page_html)
            if text[:500] not in self.seen_texts
        ]

        if not messages:
            return

        sample_size = min(len(messages), random.randint(2, 4))

        for text in random.sample(messages, sample_size):
            self._remember_text(text)
            self.queue.append(
                {
                    "source": "8kun",
                    "subject": "/qresearch/ Q Research",
                    "timestamp": datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                    "text": text,
                }
            )

    def stream(self):
        pending_thread_id = None

        while True:
            try:
                if pending_thread_id is not None:
                    thread_url = (
                        f"{self.base_url}/{self.board}/res/"
                        f"{pending_thread_id}.html"
                    )
                    thread_html = self._request_text(thread_url)
                    self._queue_thread_messages(thread_html)
                    pending_thread_id = None
                else:
                    index_url = f"{self.base_url}/{self.board}/index.html"
                    index_html = self._request_text(index_url)
                    pending_thread_id = self._choose_thread(index_html)

            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
            ) as error:
                print(f"[8kun connection error] {error}")
                pending_thread_id = None

            if self.queue:
                yield self.queue.popleft()

            time.sleep(self.poll_seconds)
