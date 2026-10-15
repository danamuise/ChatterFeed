import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime


class MastodonSource:
    """Poll a public Mastodon hashtag timeline and yield new statuses."""

    def __init__(
        self,
        hashtag: str = "art",
        instance: str = "https://mastodon.social",
        poll_seconds: float = 5.0,
    ) -> None:
        self.hashtag = hashtag.lstrip("#")
        self.instance = instance.rstrip("/")
        self.poll_seconds = poll_seconds
        self.since_id: str | None = None
        self.seen_ids: set[str] = set()

    @staticmethod
    def _plain_text(content: str) -> str:
        # Mastodon status content is HTML. Preserve paragraph/line breaks,
        # strip tags, decode entities, and normalize whitespace.
        content = re.sub(r"<br\s*/?>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"</p\s*>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"<[^>]+>", "", content)
        content = html.unescape(content)
        lines = [line.strip() for line in content.splitlines()]
        return "\n".join(line for line in lines if line).strip()

    def _fetch(self) -> list[dict]:
        params = {"limit": "20"}
        if self.since_id:
            params["since_id"] = self.since_id

        encoded_tag = urllib.parse.quote(self.hashtag, safe="")
        query = urllib.parse.urlencode(params)
        url = (
            f"{self.instance}/api/v1/timelines/tag/"
            f"{encoded_tag}?{query}"
        )

        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "ChatterFeed/0.3 (non-commercial art project)",
            },
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def stream(self):
        while True:
            try:
                statuses = self._fetch()

                if statuses:
                    # IDs are sortable decimal strings on Mastodon.
                    newest_id = max(status["id"] for status in statuses)
                    self.since_id = newest_id

                    # API returns newest first; display oldest first so the
                    # console scrolls naturally forward through time.
                    for status in reversed(statuses):
                        status_id = status["id"]
                        if status_id in self.seen_ids:
                            continue

                        self.seen_ids.add(status_id)
                        text = self._plain_text(status.get("content", ""))

                        # Ignore boosts with no useful display text.
                        if not text and status.get("reblog"):
                            text = self._plain_text(
                                status["reblog"].get("content", "")
                            )

                        if not text:
                            continue

                        created_at = status.get(
                            "created_at",
                            datetime.now().isoformat(timespec="seconds"),
                        )

                        yield {
                            "source": "mastodon.social",
                            "subject": f"#{self.hashtag}",
                            "timestamp": created_at,
                            "text": text,
                        }

            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                json.JSONDecodeError,
            ) as error:
                print(f"[Mastodon connection error] {error}")

            time.sleep(self.poll_seconds)
