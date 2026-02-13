"""Tests for ContentClassifier async wrapper."""

from istari.tools.classifier.classifier import ContentClassifier


class TestContentClassifier:
    async def test_name(self):
        classifier = ContentClassifier()
        assert classifier.name == "content_classifier"

    async def test_description(self):
        classifier = ContentClassifier()
        assert "sensitivity" in classifier.description.lower()

    async def test_execute_clean_text(self):
        classifier = ContentClassifier()
        result = await classifier.execute(text="Hello world")
        assert not result.is_sensitive

    async def test_execute_sensitive_text(self):
        classifier = ContentClassifier()
        result = await classifier.execute(text="My SSN is 123-45-6789")
        assert result.is_sensitive
        assert "pii" in result.flags
