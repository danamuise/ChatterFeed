import os
import random
import sys
import threading
import time

from openai import OpenAI

from ai_interpreter import evaluate_post
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
                print("ChatterFeed v2.4")
                print("Listening to Mastodon + Bluesky + 4chan + 8kun conversations...")
                print("Commands: c + Enter = clear | Ctrl+C = stop.\n")
        except (EOFError, KeyboardInterrupt):
            return


def main() -> None:
    # Chance of selecting a post for interpretation (0=never, 1=every post).
    interpret_chance = max(
        0.0, min(1.0, float(os.getenv("CHATTERFEED_INTERPRET_CHANCE", "0.20")))
    )
    # Time to hold an interpreted post onscreen, simulating a robot drawing.
    draw_seconds = max(0.0, float(os.getenv("CHATTERFEED_DRAW_SECONDS", "10")))

    print("ChatterFeed v2.4")
    print("Listening to Mastodon + Bluesky + 4chan + 8kun conversations...")
    print("4chan boards: /v/ /g/ /pol/ /int/ /lgbt/")
    print(f"AI interpretation: {interpret_chance:.0%} chance per post")
    print(f"Simulated drawing hold: {draw_seconds:g} seconds")
    print("Commands: c + Enter = clear | Ctrl+C = stop.\n")

    source = CombinedSource(display_seconds=5.0)
    classifier = MessageClassifier()
    client = OpenAI()
    sanitizer = MessageSanitizer(client=client)
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

            # Keep the existing (currently placeholder) classifier/trigger path.
            result = classifier.analyze(raw_text)
            triggers.handle(result)

            # Select random posts for the existing cloud AI interpreter.
            # Store the full interpretation and a prominent -100..+100 tone
            # score on the post itself for future GUI/robot integration.
            if random.random() < interpret_chance:
                try:
                    interpretation = evaluate_post(client, raw_text)
                    message["interpretation"] = interpretation
                    message["score"] = round(interpretation["valence"] * 100)
                except Exception as error:
                    # An interpretation failure should not stop the torrent.
                    print(f"[Interpreter warning] {error}", file=sys.stderr)

            # Sanitize every post before public display, including selected posts.
            safe_text = sanitizer.clean(raw_text)

            display.show(
                source=message["source"],
                subject=message["subject"],
                timestamp=message["timestamp"],
                safe_text=safe_text,
                result=result,
                interpretation=message.get("interpretation"),
                draw_seconds=draw_seconds,
            )

            # This pauses displayed posts, not the background source workers.
            # It will later be replaced by a robot READY/complete signal.
            if "interpretation" in message:
                time.sleep(draw_seconds)

    except KeyboardInterrupt:
        print("\nChatterFeed stopped.")


if __name__ == "__main__":
    main()
