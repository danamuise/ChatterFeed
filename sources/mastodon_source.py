import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime


class MastodonSource:
    """Poll a fixed set of Mastodon hashtags and yield new statuses."""

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
        ]
        self.since_ids: dict[str, str] = {}
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
                "User-Agent": "ChatterFeed/0.6 (non-commercial art project)",
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def _fetch_tag(self, hashtag: str) -> list[dict]:
        params = {"limit": "20"}
        since_id = self.since_ids.get(hashtag)
        if since_id:
            params["since_id"] = since_id

        encoded_tag = urllib.parse.quote(hashtag, safe="")
        query = urllib.parse.urlencode(params)
        url = (
            f"{self.instance}/api/v1/timelines/tag/"
            f"{encoded_tag}?{query}"
        )
        return self._request_json(url)

    def stream(self):
        print(
            "Hashtags: "
            + ", ".join(f"#{tag}" for tag in self.hashtags)
            + "\n"
        )

        while True:
            combined: list[dict] = []

            try:
                for hashtag in self.hashtags:
                    statuses = self._fetch_tag(hashtag)

                    if statuses:
                        newest_id = str(
                            max(int(status["id"]) for status in statuses)
                        )
                        self.since_ids[hashtag] = newest_id

                    for status in statuses:
                        combined.append(
                            {
                                "hashtag": hashtag,
                                "status": status,
                            }
                        )

                combined.sort(
                    key=lambda item: item["status"].get("created_at", "")
                )

                for item in combined:
                    hashtag = item["hashtag"]
                    status = item["status"]
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

                    created_at = status.get(
                        "created_at",
                        datetime.now().isoformat(timespec="seconds"),
                    )

                    yield {
                        "source": "mastodon.social",
                        "subject": f"#{hashtag}",
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
