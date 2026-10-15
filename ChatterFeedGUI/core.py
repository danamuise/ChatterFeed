from dataclasses import dataclass
from typing import Callable, Iterable

from processing.classifier import ClassificationResult, MessageClassifier
from processing.sanitizer import MessageSanitizer
from responses.robot_controller import RobotController


@dataclass
class ProcessedMessage:
    source: str
    subject: str
    timestamp: str
    safe_text: str
    classification: ClassificationResult


class ChatterFeedEngine:
    """Process source messages without depending on any particular UI."""

    def __init__(
        self,
        classifier: MessageClassifier | None = None,
        sanitizer: MessageSanitizer | None = None,
        robot: RobotController | None = None,
    ) -> None:
        self.classifier = classifier or MessageClassifier()
        self.sanitizer = sanitizer or MessageSanitizer()
        self.robot = robot or RobotController()

    def process(self, message: dict[str, str]) -> ProcessedMessage:
        raw_text = message["text"]
        result = self.classifier.analyze(raw_text)

        # Physical responses are triggered from the original text classification.
        self.robot.handle(result)

        # Only the sanitized text is passed on to display code.
        return ProcessedMessage(
            source=message["source"],
            subject=message["subject"],
            timestamp=message["timestamp"],
            safe_text=self.sanitizer.clean(raw_text),
            classification=result,
        )
