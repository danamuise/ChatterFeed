from dataclasses import dataclass


@dataclass
class ClassificationResult:
    categories: list[str]

    @property
    def matched(self) -> bool:
        return bool(self.categories)


class MessageClassifier:
    """
    Temporary rule-based classifier for the prototype.

    This is intentionally simple. Later, this module can be replaced with
    a more capable local or remote text classifier without changing the
    rest of ChatterFeed.
    """

    def __init__(self) -> None:
        self.rules = {
            "violence": {"kill", "attack", "hurt", "shoot"},
            "homophobic": {"homophobic", "anti-gay", "anti gay"},
            "sexually_explicit": {
                "sex",
                "sexual",
                "nude",
                "nudes",
                "porn",
                "pornography",
                "xxx",
            },
            # Placeholder only. Real slur detection will be added separately.
            "racism": {"example_slur"},
        }

    def analyze(self, text: str) -> ClassificationResult:
        lowered = text.lower()
        categories = []

        for category, keywords in self.rules.items():
            if any(keyword in lowered for keyword in keywords):
                categories.append(category)

        return ClassificationResult(categories=categories)
