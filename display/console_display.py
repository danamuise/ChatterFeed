from colorama import Fore, Style, just_fix_windows_console

from processing.classifier import ClassificationResult


# Enable reliable ANSI colors in Windows PowerShell / Command Prompt.
# On the Raspberry Pi, standard terminal color sequences work natively.
just_fix_windows_console()


class ConsoleDisplay:
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
        print("=" * 70)
        print(f"Source: {source}")
        print(f"Feed:   {subject}")
        print(f"Time:   {timestamp}")

        color = ""
        if interpretation is not None:
            # Valence is returned by the AI on a -1..+1 scale.
            # Show it more clearly as a tone score from -100 to +100.
            valence = float(interpretation["valence"])
            intensity = float(interpretation["intensity"])
            score = round(valence * 100)
            intensity_score = round(intensity * 100)
            if valence <= -0.2:
                color = Fore.RED
            elif valence >= 0.2:
                color = Fore.GREEN
            else:
                color = Fore.YELLOW

            # Score appears immediately under the Time line.
            print(
                f"{Style.BRIGHT}{color}"
                f"Score:  {score:+d}/100 (tone)  |  Intensity: {intensity_score}/100"
                f"{Style.RESET_ALL}"
            )
            print(f"{color}[AI INTERPRETED - DRAW HOLD {draw_seconds:g}s]{Style.RESET_ALL}")

        for category in result.categories:
            print(f"[TRIGGER] {category.upper()}")

        print()
        if interpretation is not None:
            # Temporary tint for the selected, sanitized message body.
            print(f"{Style.BRIGHT}{color}{safe_text}{Style.RESET_ALL}")
        else:
            print(safe_text)
        print()
