from processing.classifier import ClassificationResult


class ConsoleDisplay:
    def show(
        self,
        source: str,
        subject: str,
        timestamp: str,
        safe_text: str,
        result: ClassificationResult,
    ) -> None:
        print("=" * 70)
        print(f"Source: {source}")
        print(f"Feed:   {subject}")
        print(f"Time:   {timestamp}")

        for category in result.categories:
            print(f"[TRIGGER] {category.upper()}")

        print()
        print(safe_text)
        print()
