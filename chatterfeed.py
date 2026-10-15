from display.console_display import ConsoleDisplay
from processing.classifier import MessageClassifier
from processing.sanitizer import MessageSanitizer
from responses.triggers import TriggerHandler
from sources.mastodon_source import MastodonSource


def main() -> None:
    hashtag = "art"

    print("ChatterFeed v0.3")
    print(f"Listening to mastodon.social #{hashtag}...")
    print("Press Ctrl+C to stop.\n")

    source = MastodonSource(hashtag=hashtag)
    classifier = MessageClassifier()
    sanitizer = MessageSanitizer()
    triggers = TriggerHandler()
    display = ConsoleDisplay()

    try:
        for message in source.stream():
            raw_text = message["text"]

            # 1. Analyze the original raw message.
            result = classifier.analyze(raw_text)

            # 2. Trigger any related responses using the classification.
            triggers.handle(result)

            # 3. Create a sanitized copy for public display.
            safe_text = sanitizer.clean(raw_text)

            # 4. Display only the sanitized copy.
            display.show(
                source=message["source"],
                subject=message["subject"],
                timestamp=message["timestamp"],
                safe_text=safe_text,
                result=result,
            )

            # The raw message is not stored anywhere by ChatterFeed.

    except KeyboardInterrupt:
        print("\nChatterFeed stopped.")


if __name__ == "__main__":
    main()
