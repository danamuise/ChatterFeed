from processing.classifier import ClassificationResult


class ConsoleDisplay:
    def show(
        self,
        source: str,
        timestamp: str,
        safe_text: str,
        result: ClassificationResult,
    ) -> None:
        print("=" * 70)
        print(f"Subreddit: {source}")
        print(f"Time:   {timestamp}")

        if result.categories:
            print(f"Tags:   {', '.join(result.categories)}")

        print()
        print(safe_text)
        print()
