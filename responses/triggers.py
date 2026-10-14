from processing.classifier import ClassificationResult


class TriggerHandler:
    """
    Prototype trigger handler.

    For now this prints the detected categories. Later this is where
    GPIO, motors, servos, solenoids, lights, sound, or other artwork
    responses can be connected.
    """

    def handle(self, result: ClassificationResult) -> None:
        for category in result.categories:
            print(f"[TRIGGER] {category.upper()}")
