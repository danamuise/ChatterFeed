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
    """Poll hashtags and public thread replies one request at a time."""

    def __init__(
        self,
        instance: str = "https://mastodon.social",
        poll_seconds: float = 5.0,
        request_lock=None,
    ) -> None:
        self.instance = instance.rstrip("/")
        self.poll_seconds = poll_seconds
        self.request_lock = request_lock
        self.hashtags = [
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
            "mastodon",
            "life",
            "thoughts",
            "chat",
            "sex",
            "homosexual",
            "transexual",
            "rightwing",
        ]
        self.since_ids: dict[str, str] = {}

        # Keep duplicate detection bounded so a long-running installation
        # does not accumulate an ever-growing set of post IDs.
        self.max_seen_ids = 2000
        self.seen_ids: set[str] = set()
        self.seen_id_order: deque[str] = deque()

        # Keep standalone posts and thread replies separate so replies can
        # dominate the torrent without allowing memory to grow forever.
        self.standalone_queue: deque[dict] = deque(maxlen=300)
        self.thread_queue: deque[dict] = deque(maxlen=300)
        self.last_subject: str | None = None
        self.thread_display_count = 0

        # At most one thread-context request is pending at a time. This keeps
        # the network pattern strictly sequential:
        # hashtag request -> thread request -> next hashtag request.
        self.pending_thread: dict | None = None

        # Avoid repeatedly sampling the same active thread.
        self.recent_thread_ids: deque[str] = deque(maxlen=100)

    @staticmethod
    def _plain_text(content: str) -> str:
        content = re.sub(r"<br\s*/?>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"</p\s*>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"<[^>]+>", "", content)
        content = html.unescape(content)
        lines = [line.strip() for line in content.splitlines()]
        return "\n".join(line for line in lines if line).strip()

    def _request_json(self, url: str):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "ChatterFeed/1.9 (non-commercial art project)",
            },
        )

        try:
            if self.request_lock is None:
                with urllib.request.urlopen(request, timeout=15) as response:
                    return json.loads(response.read().decode("utf-8"))

            with self.request_lock:
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
                return None

            raise

    def _fetch_trending_statuses(self) -> list[dict]:
        url = f"{self.instance}/api/v1/trends/statuses?limit=40"
        result = self._request_json(url)
        return result if isinstance(result, list) else []

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
        result = self._request_json(url)
        return result if isinstance(result, list) else []

    def _fetch_thread_context(self, status_id: str) -> dict:
        url = f"{self.instance}/api/v1/statuses/{status_id}/context"
        result = self._request_json(url)
        return result if isinstance(result, dict) else {}

    @staticmethod
    def _contains_non_latin_script(text: str) -> bool:
        # Mastodon's language metadata is not always present or accurate.
        # Reject posts containing a meaningful amount of non-Latin script
        # so obvious Japanese/Chinese/Korean/Cyrillic/Arabic/etc. text does
        # not enter the English-only torrent.
        non_latin_patterns = [
            r"[\u3040-\u30ff]",  # Hiragana + Katakana
            r"[\u3400-\u4dbf\u4e00-\u9fff]",  # CJK ideographs
            r"[\uac00-\ud7af]",  # Hangul
            r"[\u0400-\u04ff]",  # Cyrillic
            r"[\u0590-\u05ff]",  # Hebrew
            r"[\u0600-\u06ff]",  # Arabic
            r"[\u0900-\u097f]",  # Devanagari
            r"[\u0e00-\u0e7f]",  # Thai
        ]

        count = 0
        for pattern in non_latin_patterns:
            count += len(re.findall(pattern, text))

        return count >= 4

    @classmethod
    def _should_ignore(cls, text: str) -> bool:
        if len(text) >= 1000:
            return True

        if cls._contains_non_latin_script(text):
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

    def _queue_one_status(
        self,
        subject: str,
        status: dict,
        is_thread_reply: bool = False,
    ) -> None:
        status_id = status.get("id")
        if not status_id or status_id in self.seen_ids:
            return

        self._remember_seen_id(status_id)

        text = self._plain_text(status.get("content", ""))

        if not text and status.get("reblog"):
            text = self._plain_text(
                status["reblog"].get("content", "")
            )

        if not text:
            return

        language = status.get("language")
        if language and language.lower() != "en":
            return

        if self._should_ignore(text):
            return

        created_at = status.get(
            "created_at",
            datetime.now().isoformat(timespec="seconds"),
        )

        message = {
            "source": "mastodon.social",
            "subject": subject,
            "timestamp": created_at,
            "text": text,
        }

        if is_thread_reply:
            self.thread_queue.append(message)
        else:
            self.standalone_queue.append(message)

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
            self._queue_one_status(f"#{hashtag}", status, False)

    def _matching_monitored_tags(self, status: dict) -> list[str]:
        status_tags = {
            tag.get("name", "").lower()
            for tag in status.get("tags", [])
        }
        return [
            hashtag
            for hashtag in self.hashtags
            if hashtag.lower() in status_tags
        ]

    def _choose_thread_candidate(
        self,
        subject: str | None,
        statuses: list[dict],
        require_monitored_tag: bool = False,
    ) -> None:
        candidates: list[tuple[dict, list[str]]] = []

        for status in statuses:
            if int(status.get("replies_count", 0) or 0) <= 0:
                continue

            status_id = status.get("id")
            if not status_id or status_id in self.recent_thread_ids:
                continue

            matches = self._matching_monitored_tags(status)
            if require_monitored_tag and not matches:
                continue

            candidates.append((status, matches))

        if not candidates:
            self.pending_thread = None
            return

        chosen, matches = random.choice(candidates)
        chosen_subject = subject

        if matches:
            chosen_subject = f"#{random.choice(matches)}"

        self.pending_thread = {
            "status_id": chosen["id"],
            "subject": chosen_subject or "THREAD",
        }
        self.recent_thread_ids.append(chosen["id"])

    def _queue_thread_replies(self, subject: str, context: dict) -> None:
        descendants = context.get("descendants", [])
        if not isinstance(descendants, list) or not descendants:
            return

        # Take only a small random sample so one active thread cannot dominate
        # the torrent. The next discovery cycle moves on to another thread.
        sample_size = min(len(descendants), random.randint(2, 4))
        for reply in random.sample(descendants, sample_size):
            self._queue_one_status(subject, reply, True)

    def _pop_random_message(self, queue: deque[dict]) -> dict | None:
        if not queue:
            return None

        eligible_indexes = [
            index
            for index, message in enumerate(queue)
            if message["subject"] != self.last_subject
        ]

        if not eligible_indexes:
            eligible_indexes = list(range(len(queue)))

        chosen_index = random.choice(eligible_indexes)
        queue.rotate(-chosen_index)
        message = queue.popleft()
        queue.rotate(chosen_index)
        return message

    def _next_queued_message(self) -> dict | None:
        message = None

        # Favor thread replies 4:1 whenever both queues contain content.
        if self.thread_queue and (
            self.thread_display_count < 4 or not self.standalone_queue
        ):
            message = self._pop_random_message(self.thread_queue)
            if message:
                self.thread_display_count += 1
        elif self.standalone_queue:
            message = self._pop_random_message(self.standalone_queue)
            if message:
                self.thread_display_count = 0
        elif self.thread_queue:
            message = self._pop_random_message(self.thread_queue)
            if message:
                self.thread_display_count += 1

        if message:
            self.last_subject = message["subject"]

        return message

    def stream(self):
        print(
            "Conversation discovery: trending Mastodon statuses + thread context"
        )
        print(
            "Fallback hashtags: "
            + ", ".join(f"#{tag}" for tag in self.hashtags)
            + "\n"
        )

        hashtag_index = 0
        fetch_thread_next = False
        use_hashtag_fallback = False

        while True:
            try:
                if fetch_thread_next and self.pending_thread:
                    context = self._fetch_thread_context(
                        self.pending_thread["status_id"]
                    )
                    self._queue_thread_replies(
                        self.pending_thread["subject"],
                        context,
                    )
                    self.pending_thread = None
                    fetch_thread_next = False

                else:
                    # Primary discovery: public statuses with unusually high
                    # interaction. These are more likely to have replies than
                    # random hashtag posts.
                    statuses = self._fetch_trending_statuses()
                    self._choose_thread_candidate(
                        None,
                        statuses,
                        require_monitored_tag=True,
                    )

                    if self.pending_thread is not None:
                        fetch_thread_next = True
                        use_hashtag_fallback = False
                    else:
                        # If the trending-status discovery yields no replied-to
                        # posts, fall back to one of the selected hashtags.
                        hashtag = self.hashtags[hashtag_index]
                        tag_statuses = self._fetch_tag(hashtag)

                        if tag_statuses:
                            newest_id = str(
                                max(int(status["id"]) for status in tag_statuses)
                            )
                            self.since_ids[hashtag] = newest_id

                        self._choose_thread_candidate(
                            f"#{hashtag}",
                            tag_statuses,
                            require_monitored_tag=False,
                        )

                        if self.pending_thread is None and tag_statuses:
                            fallback = random.choice(tag_statuses)
                            self._queue_one_status(
                                f"#{hashtag}",
                                fallback,
                                False,
                            )

                        hashtag_index = (
                            hashtag_index + 1
                        ) % len(self.hashtags)
                        fetch_thread_next = self.pending_thread is not None
                        use_hashtag_fallback = True

            except (
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
            ) as error:
                print(f"[Mastodon connection error] {error}")
                self.pending_thread = None
                fetch_thread_next = False

            message = self._next_queued_message()
            if message:
                yield message

            time.sleep(self.poll_seconds)
