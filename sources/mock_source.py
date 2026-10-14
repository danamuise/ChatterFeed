import random
import time
from datetime import datetime


class MockSource:
    """Generate fake messages so the streaming pipeline can be tested."""

    def __init__(self) -> None:
        self.messages = [
            "This is a sample public comment.",
            "Another message just appeared.",
            "People are discussing today's news.",
            "This is a simulated social media post.",
            "That post contains homophobic language.",
            "Someone said they wanted to attack the other team.",
            "What the fuck is happening here?",
            "This contains example_slur so we can test solid-block redaction.",
            "Someone posted explicit porn content.",
            "The conversation keeps moving.",
            "A new comment was posted.",
        ]

    def stream(self):
        while True:
            time.sleep(random.uniform(0.5, 2.5))

            yield {
                "source": "mock",
                "subject": "mock",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "text": random.choice(self.messages),
            }
