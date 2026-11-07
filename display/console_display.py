import sys
import time

from concurrent.futures import Future
from colorama import Fore, Style, just_fix_windows_console
from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

from processing.classifier import ClassificationResult
from marker_palette import emotion_to_marker


# Colorama enables console ANSI support on Windows.
just_fix_windows_console()


def display_source(source: str) -> str:
    """Add source-specific emoji to torrent source labels only."""
    if source.casefold() == "4chan":
        return f"{source} 🍀"
    if source.casefold().startswith("mastodon"):
        return f"{source} 🦣"
    if source.casefold() == "8kun":
        return f"{source} 8️⃣"
    if source.casefold() == "bluesky":
        return f"{source} 🦋"
    return source


class ConsoleDisplay:
    def __init__(self) -> None:
        self.console = Console()

    def show(
        self,
        source: str,
        subject: str,
        timestamp: str,
        safe_text: str,
        result: ClassificationResult,
        interpretation: dict | None = None,
        draw_seconds: float = 10.0,
    ) -> None:
        """Normal, unselected torrent entry."""
        print("=" * 70)
        print(f"Source: {display_source(source)}")
        print(f"Feed:   {subject}")
        print(f"Time:   {timestamp}")

        for category in result.categories:
            print(f"[TRIGGER] {category.upper()}")

        print()
        print(safe_text)
        print()

    @staticmethod
    def _selected_entry(
        source: str,
        subject: str,
        timestamp: str,
        safe_text: str,
        result: ClassificationResult,
        hold_seconds: float,
        interpretation: dict | None = None,
        error: str | None = None,
    ) -> Group:
        """Make a replaceable terminal entry, keeping Score under Time."""
        if interpretation is not None:
            valence = float(interpretation["valence"])
            intensity = float(interpretation["intensity"])
            marker = emotion_to_marker(interpretation)
            color = f"bold {marker.hex_color}"
            score_line = Text(
                f"Score:  {round(valence * 100):+d}/100 (tone)  |  "
                f"Intensity: {round(intensity * 100)}/100",
                style=color,
            )
            rationale = str(interpretation.get("rationale", "")).strip()
            rationale_line = Text(
                f"Rationale: {rationale}" if rationale else "Rationale: not provided",
                style=color,
            )
            status = Text(
                f"[AI INTERPRETED - MARKER {marker.number}: {marker.name} "
                f"({marker.emotion}) - DRAW HOLD {hold_seconds:g}s]",
                style=color,
            )
        elif error:
            color = "bold magenta"
            score_line = Text("Score:  unavailable (AI interpretation failed)", style=color)
            status = Text(f"[DRAW HOLD {hold_seconds:g}s]", style=color)
        else:
            color = "bold cyan"
            score_line = Text("Score:  interpreting with AI...", style=color)
            status = Text(f"[AI SELECTED - DRAW HOLD {hold_seconds:g}s]", style=color)

        lines = [
            Text("=" * 70),
            Text(f"Source: {display_source(source)}"),
            Text(f"Feed:   {subject}"),
            Text(f"Time:   {timestamp}"),
            score_line,
            *([rationale_line] if interpretation is not None else []),
            status,
        ]
        for category in result.categories:
            lines.append(Text(f"[TRIGGER] {category.upper()}"))

        lines.extend([Text(""), Text(safe_text, style=color), Text("")])
        return Group(*lines)

    def show_selected(
        self,
        source: str,
        subject: str,
        timestamp: str,
        safe_text: str,
        result: ClassificationResult,
        interpretation_future: Future,
        hold_seconds: float = 10.0,
    ) -> dict | None:
        """Show sanitized text promptly, then update its score in place.

        The simulated drawing timer starts on the initial rendering, not
        before the AI calls. Wait at least hold_seconds and for a score,
        with a 30-second upper bound to avoid hanging on a failed API.
        """
        started = time.monotonic()
        interpretation = None
        completed = False

        initial = self._selected_entry(
            source, subject, timestamp, safe_text, result, hold_seconds
        )
        with Live(
            initial,
            console=self.console,
            auto_refresh=True,
            refresh_per_second=8,
            transient=False,
            vertical_overflow="visible",
        ) as live:
            while True:
                if not completed and interpretation_future.done():
                    completed = True
                    try:
                        interpretation = interpretation_future.result()
                        updated = self._selected_entry(
                            source, subject, timestamp, safe_text, result,
                            hold_seconds, interpretation=interpretation,
                        )
                    except Exception as exc:
                        print(f"[Interpreter warning] {exc}", file=sys.stderr)
                        updated = self._selected_entry(
                            source, subject, timestamp, safe_text, result,
                            hold_seconds, error=str(exc),
                        )
                    live.update(updated, refresh=True)

                elapsed = time.monotonic() - started
                if elapsed >= hold_seconds and completed:
                    break
                if elapsed >= max(hold_seconds, 30.0):
                    if not completed:
                        live.update(
                            self._selected_entry(
                                source, subject, timestamp, safe_text, result,
                                hold_seconds, error="AI response timeout",
                            ),
                            refresh=True,
                        )
                        print("[Interpreter warning] Timed out waiting for a score", file=sys.stderr)
                    break
                time.sleep(0.05)

        return interpretation
