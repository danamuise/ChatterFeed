import os
import threading

from display.console_display import ConsoleDisplay
from processing.classifier import MessageClassifier
from processing.sanitizer import MessageSanitizer
from responses.triggers import TriggerHandler
from sources.mastodon_source import MastodonSource


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def keyboard_commands() -> None:
    """Listen for simple console commands without interrupting the feed."""
    while True:
        try:
            command = input().strip().lower()
            if command in {"c", "clear"}:
                clear_screen()
                print("ChatterFeed v0.5")
                print("Listening to mastodon.social top 5 trending hashtags...")
                print("Commands: c + Enter = clear | Ctrl+C = stop.\n")
        except (EOFError, KeyboardInterrupt):
            return


def main() -> None:
    print("ChatterFeed v0.5")
    print("Listening to mastodon.social top 5 trending hashtags...")
    print("Commands: c + Enter = clear | Ctrl+C = stop.\n")

    source = MastodonSource(tag_count=5)
    classifier = MessageClassifier()
    sanitizer = MessageSanitizer()
    triggers = TriggerHandler()
    display = ConsoleDisplay()

    command_thread = threading.Thread(
        target=keyboard_commands,
        daemon=True,
    )
    command_thread.start()

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
