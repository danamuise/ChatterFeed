from core import ChatterFeedEngine
from display.console_display import ConsoleDisplay
from sources.mock_source import MockSource


def main() -> None:
    print("ChatterFeed v0.3")
    print("Listening for messages...")
    print("Press Ctrl+C to stop.\n")

    source = MockSource()
    engine = ChatterFeedEngine()
    display = ConsoleDisplay()

    try:
        for message in source.stream():
            processed = engine.process(message)
            display.show(
                source=processed.source,
                subject=processed.subject,
                timestamp=processed.timestamp,
                safe_text=processed.safe_text,
                result=processed.classification,
            )
    except KeyboardInterrupt:
        print("\nChatterFeed stopped.")


if __name__ == "__main__":
    main()
