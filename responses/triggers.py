from processing.classifier import ClassificationResult


class TriggerHandler:
    """
    Prototype trigger handler.

    For now this method is a placeholder for future physical responses.
    The console display prints trigger labels so they stay visually grouped
    with the message that caused them.
    """

    def handle(self, result: ClassificationResult) -> None:
        # Later: trigger GPIO, motors, servos, solenoids, lights, sound, etc.
        pass
