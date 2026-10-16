import queue
import random
import threading
import time

from sources.bluesky_source import BlueskySource
from sources.fourchan_source import FourChanSource
from sources.mastodon_source import MastodonSource


class CombinedSource:
    """Merge Mastodon, Bluesky, and 4chan into one paced ChatterFeed torrent."""

    def __init__(self, display_seconds: float = 5.0) -> None:
        self.display_seconds = display_seconds
        self.request_lock = threading.Lock()
        self.output: queue.Queue[dict] = queue.Queue(maxsize=500)

        self.sources = [
            MastodonSource(
                poll_seconds=5.0,
                request_lock=self.request_lock,
            ),
            BlueskySource(
                poll_seconds=5.0,
                request_lock=self.request_lock,
            ),
            FourChanSource(
                poll_seconds=5.0,
                request_lock=self.request_lock,
            ),
        ]

    def _worker(self, source) -> None:
        for message in source.stream():
            try:
                self.output.put_nowait(message)
            except queue.Full:
                try:
                    self.output.get_nowait()
                except queue.Empty:
                    pass

                try:
                    self.output.put_nowait(message)
                except queue.Full:
                    pass

    def stream(self):
        threads = []

        for source in self.sources:
            thread = threading.Thread(
                target=self._worker,
                args=(source,),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        pending: list[dict] = []
        last_source = None

        while True:
            try:
                while len(pending) < 20:
                    pending.append(
                        self.output.get(timeout=1.0)
                    )
            except queue.Empty:
                pass

            if pending:
                different_source = [
                    message
                    for message in pending
                    if message.get("source") != last_source
                ]

                candidates = different_source or pending
                message = random.choice(candidates)
                pending.remove(message)
                last_source = message.get("source")

                yield message

            time.sleep(self.display_seconds)
