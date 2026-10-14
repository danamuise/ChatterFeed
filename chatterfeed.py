from sources.mock_source import MockSource


def handle_message(message: dict) -> None:
    """Print one incoming message. Nothing is stored."""
    print("=" * 70)
    print(f"Source: {message['source']}")
    print(f"Time:   {message['timestamp']}")
    print()
    print(message["text"])
    print()


def main() -> None:
    print("ChatterFeed v0.1")
    print("Listening for messages...")
    print("Press Ctrl+C to stop.\n")

    source = MockSource()

    try:
        for message in source.stream():
            handle_message(message)
    except KeyboardInterrupt:
        print("\nChatterFeed stopped.")


if __name__ == "__main__":
    main()
