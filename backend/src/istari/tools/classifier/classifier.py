"""Content sensitivity classifier — runs locally, never touches cloud APIs."""

from istari.tools.classifier.rules import ClassificationResult, classify


class ContentClassifier:
    """Tool wrapper around the rule-based content classifier."""

    @property
    def name(self) -> str:
        return "content_classifier"

    @property
    def description(self) -> str:
        return "Classifies text for sensitivity (PII, financial, email, file content)"

    async def execute(self, *, text: str) -> ClassificationResult:
        """Classify text sensitivity. Always runs locally, never touches cloud APIs."""
        return classify(text)
