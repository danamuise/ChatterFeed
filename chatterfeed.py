import os
import random
import threading

from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

from ai_interpreter import evaluate_post
from display.console_display import ConsoleDisplay
from marker_palette import emotion_to_marker
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
                print("ChatterFeed v2.5")
                print("Listening to Mastodon + Bluesky + 4chan + 8kun conversations...")
                print("Commands: c + Enter = clear | Ctrl+C = stop.\n")
        except (EOFError, KeyboardInterrupt):
            return


def main() -> None:
    # Interpret one post every 4 to 7 posts, with a fresh random interval
    # after each selection. This avoids long runs without robot activity.
    min_interval = 4
    max_interval = 7
    posts_until_interpretation = random.randint(min_interval, max_interval)
    draw_seconds = max(0.0, float(os.getenv("CHATTERFEED_DRAW_SECONDS", "10")))

    print("ChatterFeed v2.5")
    print("Listening to Mastodon + Bluesky + 4chan + 8kun conversations...")
    print("4chan boards: /v/ /g/ /pol/ /int/ /lgbt/")
    print(f"AI interpretation: every {min_interval}-{max_interval} posts (random interval)")
    print("Marker color: emotion-based (tone score is separate)")
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

    # The interpreter runs separately from the sanitizer so it does not
    # delay the appearance of the sanitized post in the torrent.
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="interpreter") as interpreter_pool:
            for message in source.stream():
                raw_text = message["text"]

                # Keep the existing (currently placeholder) classifier/trigger path.
                result = classifier.analyze(raw_text)
                triggers.handle(result)

                posts_until_interpretation -= 1
                selected = posts_until_interpretation == 0
                if selected:
                    posts_until_interpretation = random.randint(
                        min_interval, max_interval
                    )
                interpretation_future = (
                    interpreter_pool.submit(evaluate_post, client, raw_text)
                    if selected else None
                )

                # Never show raw post text: wait for AI sanitization first.
                safe_text = sanitizer.clean(raw_text)

                if selected:
                    # Display immediately after sanitization with an "interpreting"
                    # placeholder; the score and color update IN PLACE when AI
                    # interpretation completes. Hold starts on first display.
                    interpretation = display.show_selected(
                        source=message["source"],
                        subject=message["subject"],
                        timestamp=message["timestamp"],
                        safe_text=safe_text,
                        result=result,
                        interpretation_future=interpretation_future,
                        hold_seconds=draw_seconds,
                    )
                    if interpretation is not None:
                        message["interpretation"] = interpretation
                        message["score"] = round(interpretation["valence"] * 100)
                        message["marker_number"] = emotion_to_marker(interpretation).number
                else:
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
