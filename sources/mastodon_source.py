import html
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime
from email.utils import parsedate_to_datetime


class MastodonSource:
    """Poll one Mastodon hashtag at a time and emit one queued post per cycle."""

    def __init__(
        self,
        instance: str = "https://mastodon.social",
        poll_seconds: float = 5.0,
    ) -> None:
        self.instance = instance.rstrip("/")
        self.poll_seconds = poll_seconds
        self.hashtags = [
            "politics",
            "humanrights",
            "news",
            "technology",
            "climate",
            "science",
            "lgbtq",
            "culture",
            "israel",
            "palestine",
            "iran",
            "christianity",
            "jewish",
            "feminism",
            "progressive",
            "religion",
            "mastodon",
            "fediverse",
            "life",
            "thoughts",
            "chat",
        ]
        self.since_ids: dict[str, str] = {}

        # Keep duplicate detection bounded so a long-running installation
        # does not accumulate an ever-growing set of post IDs.
        self.max_seen_ids = 2000
        self.seen_ids: set[str] = set()
        self.seen_id_order: deque[str] = deque()

        # The torrent is transient. If fetching ever outruns display, discard
        # the oldest queued posts rather than allowing memory to grow forever.
        self.queue: deque[dict] = deque(maxlen=500)
        self.last_subject: str | None = None

    @staticmethod
    def _plain_text(content: str) -> str:
        content = re.sub(r"<br\s*/?>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"</p\s*>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"<[^>]+>", "", content)
        content = html.unescape(content)
        lines = [line.strip() for line in content.splitlines()]
        return "\n".join(line for line in lines if line).strip()

    def _request_json(self, url: str) -> list[dict]:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "ChatterFeed/1.2 (non-commercial art project)",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as error:
            if error.code == 429:
                retry_after = error.headers.get("Retry-After")
                wait_seconds = 60.0

                if retry_after:
                    try:
                        wait_seconds = float(retry_after)
                    except ValueError:
                        try:
                            reset_time = parsedate_to_datetime(retry_after)
                            wait_seconds = max(
                                1.0,
                                reset_time.timestamp() - time.time(),
                            )
                        except (TypeError, ValueError):
                            pass

                print(
                    f"[Mastodon rate limit] Pausing "
                    f"{int(wait_seconds)} seconds..."
                )
                time.sleep(wait_seconds)
                return []

            raise

    def _fetch_tag(self, hashtag: str) -> list[dict]:
        params: list[tuple[str, str]] = [("limit", "20")]

        since_id = self.since_ids.get(hashtag)
        if since_id:
            params.append(("since_id", since_id))

        encoded_tag = urllib.parse.quote(hashtag, safe="")
        query = urllib.parse.urlencode(params)
        url = (
            f"{self.instance}/api/v1/timelines/tag/"
            f"{encoded_tag}?{query}"
        )
        return self._request_json(url)

    @staticmethod
    def _should_ignore(text: str) -> bool:
        if len(text) >= 1000:
            return True

        url_count = len(
            re.findall(r"https?://\S+", text, flags=re.IGNORECASE)
        )
        return url_count > 2

    def _remember_seen_id(self, status_id: str) -> None:
        if status_id in self.seen_ids:
            return

        self.seen_ids.add(status_id)
        self.seen_id_order.append(status_id)

        while len(self.seen_id_order) > self.max_seen_ids:
            expired_id = self.seen_id_order.popleft()
            self.seen_ids.discard(expired_id)

    def _queue_statuses(self, hashtag: str, statuses: list[dict]) -> None:
        if statuses:
            newest_id = str(
                max(int(status["id"]) for status in statuses)
            )
            self.since_ids[hashtag] = newest_id

        statuses.sort(
            key=lambda status: status.get("created_at", "")
        )

        for status in statuses:
            status_id = status["id"]

            if status_id in self.seen_ids:
                continue

            self._remember_seen_id(status_id)
            text = self._plain_text(status.get("content", ""))

            if not text and status.get("reblog"):
                text = self._plain_text(
                    status["reblog"].get("content", "")
                )

            if not text:
                continue

            if self._should_ignore(text):
                continue

            created_at = status.get(
                "created_at",
                datetime.now().isoformat(timespec="seconds"),
            )

            self.queue.append(
                {
                    "source": "mastodon.social",
                    "subject": f"#{hashtag}",
                    "timestamp": created_at,
                    "text": text,
                }
            )

    def _next_queued_message(self) -> dict | None:
        if not self.queue:
            return None

        eligible_indexes = [
            index
            for index, message in enumerate(self.queue)
            if message["subject"] != self.last_subject
        ]

        if not eligible_indexes:
            eligible_indexes = list(range(len(self.queue)))

        chosen_index = random.choice(eligible_indexes)
        self.queue.rotate(-chosen_index)
        message = self.queue.popleft()
        self.queue.rotate(chosen_index)

        self.last_subject = message["subject"]
        return message

    def stream(self):
        print(
            "Hashtags: "
            + ", ".join(f"#{tag}" for tag in self.hashtags)
            + "\n"
        )

        hashtag_index = 0

        while True:
            hashtag = self.hashtags[hashtag_index]

            try:
                statuses = self._fetch_tag(hashtag)
                self._queue_statuses(hashtag, statuses)

            except (
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
            ) as error:
                print(f"[Mastodon connection error] {error}")

            message = self._next_queued_message()
            if message:
                yield message

            hashtag_index = (hashtag_index + 1) % len(self.hashtags)
            time.sleep(self.poll_seconds)
