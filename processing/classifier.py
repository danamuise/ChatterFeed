from dataclasses import dataclass


@dataclass
class ClassificationResult:
    categories: list[str]

    @property
    def matched(self) -> bool:
        return bool(self.categories)


class MessageClassifier:
    """
    Placeholder classifier for the current ChatterFeed prototype.

    Keyword-based detection has been removed. This module is intentionally
    neutral until it is replaced by the new context-aware AI interpretation
    strategy.
    """

    def analyze(self, text: str) -> ClassificationResult:
        return ClassificationResult(categories=[])
