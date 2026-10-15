from processing.classifier import ClassificationResult


class RobotController:
    """Hardware boundary for the eventual Raspberry Pi robot arm.

    For now this is deliberately a no-op. Later, category-specific arm
    movements can be implemented here without changing the feed, classifier,
    sanitizer, or GUI.
    """

    def handle(self, result: ClassificationResult) -> None:
        for category in result.categories:
            self.trigger(category)

    def trigger(self, category: str) -> None:
        # Future examples:
        # - send a serial command to an arm controller
        # - set GPIO outputs
        # - choose a mark-making gesture based on category/severity
        pass

    def test(self) -> str:
        """Return a harmless status string until physical hardware is attached."""
        return "Robot controller ready (simulation mode)"
