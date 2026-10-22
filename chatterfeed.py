import os
import threading

from display.console_display import ConsoleDisplay
from processing.classifier import MessageClassifier
from processing.sanitizer import MessageSanitizer
from responses.triggers import TriggerHandler
from sources.combined_source import CombinedSource


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def keyboard_commands() -> None:
    """Listen for simple console commands without interrupting the feed."""
    while True:
        try:
            command = input().strip().lower()
            if command in {"c", "clear"}:
                clear_screen()
                print("ChatterFeed v2.3")
                print("Listening to Mastodon + Bluesky + 4chan + 8kun conversations...")
                print("Commands: c + Enter = clear | Ctrl+C = stop.\n")
        except (EOFError, KeyboardInterrupt):
            return


def main() -> None:
    print("ChatterFeed v2.3")
    print("Listening to Mastodon + Bluesky + 4chan + 8kun conversations...")
    print("4chan boards: /v/ /g/ /pol/ /int/ /lgbt/")
    print("Commands: c + Enter = clear | Ctrl+C = stop.\n")

    source = CombinedSource(display_seconds=5.0)
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

            # Analyze and trigger from the untouched original post.
            result = classifier.analyze(raw_text)
            triggers.handle(result)

            # Sanitization happens only after analysis, immediately before display.
            safe_text = sanitizer.clean(raw_text)

            display.show(
                source=message["source"],
                subject=message["subject"],
                timestamp=message["timestamp"],
                safe_text=safe_text,
                result=result,
            )

    except KeyboardInterrupt:
        print("\nChatterFeed stopped.")


if __name__ == "__main__":
    main()
