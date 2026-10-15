import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.utils import parsedate_to_datetime


class MastodonSource:
    """Poll a fixed set of Mastodon hashtags and yield new statuses."""

    def __init__(
        self,
        instance: str = "https://mastodon.social",
        poll_seconds: float = 10.0,
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
        ]
        self.groups = [
            self.hashtags[i : i + 4]
            for i in range(0, len(self.hashtags), 4)
        ]
        self.since_ids: dict[int, str] = {}
        self.seen_ids: set[str] = set()

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
                "User-Agent": "ChatterFeed/0.7 (non-commercial art project)",
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

    def _fetch_group(self, group_index: int, tags: list[str]) -> list[dict]:
        primary = tags[0]
        params: list[tuple[str, str]] = [("limit", "40")]

        for tag in tags[1:]:
            params.append(("any[]", tag))

        since_id = self.since_ids.get(group_index)
        if since_id:
            params.append(("since_id", since_id))

        encoded_tag = urllib.parse.quote(primary, safe="")
        query = urllib.parse.urlencode(params)
        url = (
            f"{self.instance}/api/v1/timelines/tag/"
            f"{encoded_tag}?{query}"
        )
        return self._request_json(url)

    def _matched_hashtags(self, status: dict) -> list[str]:
        status_tags = {
            tag.get("name", "").lower()
            for tag in status.get("tags", [])
        }
        matches = [
            hashtag
            for hashtag in self.hashtags
            if hashtag.lower() in status_tags
        ]
        return matches

    def stream(self):
        print(
            "Hashtags: "
            + ", ".join(f"#{tag}" for tag in self.hashtags)
            + "\n"
        )

        while True:
            combined: list[dict] = []

            try:
                for group_index, tags in enumerate(self.groups):
                    statuses = self._fetch_group(group_index, tags)

                    if statuses:
                        newest_id = str(
                            max(int(status["id"]) for status in statuses)
                        )
                        self.since_ids[group_index] = newest_id

                    combined.extend(statuses)

                combined.sort(
                    key=lambda status: status.get("created_at", "")
                )

                for status in combined:
                    status_id = status["id"]

                    if status_id in self.seen_ids:
                        continue

                    self.seen_ids.add(status_id)
                    text = self._plain_text(status.get("content", ""))

                    if not text and status.get("reblog"):
                        text = self._plain_text(
                            status["reblog"].get("content", "")
                        )

                    if not text:
                        continue

                    matches = self._matched_hashtags(status)
                    subject = (
                        ", ".join(f"#{tag}" for tag in matches)
                        if matches
                        else "#unknown"
                    )

                    created_at = status.get(
                        "created_at",
                        datetime.now().isoformat(timespec="seconds"),
                    )

                    yield {
                        "source": "mastodon.social",
                        "subject": subject,
                        "timestamp": created_at,
                        "text": text,
                    }

            except (
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
            ) as error:
                print(f"[Mastodon connection error] {error}")

            time.sleep(self.poll_seconds)
