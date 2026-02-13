"""Tests for rule-based content classifier."""

from istari.tools.classifier.rules import classify


class TestCleanText:
    def test_clean_greeting(self):
        result = classify("Hello, how are you?")
        assert not result.is_sensitive
        assert result.flags == []
        assert result.matched_rules == []
        assert result.confidence == 0.0

    def test_clean_todo(self):
        result = classify("Buy groceries and pick up dry cleaning")
        assert not result.is_sensitive

    def test_empty_string(self):
        result = classify("")
        assert not result.is_sensitive


class TestPII:
    def test_email_address(self):
        result = classify("Contact me at john@example.com for details")
        assert result.is_sensitive
        assert "pii" in result.flags
        assert "email_address" in result.matched_rules

    def test_phone_number(self):
        result = classify("Call me at (555) 123-4567")
        assert result.is_sensitive
        assert "pii" in result.flags
        assert "phone_number" in result.matched_rules

    def test_ssn(self):
        result = classify("My SSN is 123-45-6789")
        assert result.is_sensitive
        assert "pii" in result.flags
        assert "ssn" in result.matched_rules

    def test_named_person(self):
        result = classify("Schedule a meeting with Dr. Smith tomorrow")
        assert result.is_sensitive
        assert "pii" in result.flags
        assert "named_person" in result.matched_rules

    def test_street_address(self):
        result = classify("Send it to 123 Main St")
        assert result.is_sensitive
        assert "pii" in result.flags
        assert "street_address" in result.matched_rules


class TestFinancial:
    def test_credit_card_visa(self):
        result = classify("Card number: 4111 1111 1111 1111")
        assert result.is_sensitive
        assert "financial" in result.flags
        assert "credit_card" in result.matched_rules

    def test_large_dollar_amount(self):
        result = classify("The invoice total is $12,500.00")
        assert result.is_sensitive
        assert "financial" in result.flags
        assert "large_dollar_amount" in result.matched_rules

    def test_bank_keyword(self):
        result = classify("Please send the wire transfer by Friday")
        assert result.is_sensitive
        assert "financial" in result.flags
        assert "bank_keyword" in result.matched_rules

    def test_small_dollar_not_flagged(self):
        result = classify("Coffee costs $5")
        assert "financial" not in result.flags


class TestEmailContent:
    def test_email_header(self):
        result = classify("From: boss@company.com\nSubject: Meeting notes")
        assert result.is_sensitive
        assert "email_content" in result.flags
        assert "email_header" in result.matched_rules

    def test_forwarded_message(self):
        result = classify("------ Forwarded message ------\nHi team")
        assert result.is_sensitive
        assert "email_content" in result.flags
        assert "forwarded_message" in result.matched_rules


class TestFileContent:
    def test_file_path_unix(self):
        result = classify("Check the file at /Users/john/Documents/report.pdf")
        assert result.is_sensitive
        assert "file_content" in result.flags
        assert "file_path" in result.matched_rules

    def test_file_path_windows(self):
        result = classify(r"Open C:\Users\john\Desktop\notes.txt")
        assert result.is_sensitive
        assert "file_content" in result.flags
        assert "file_path" in result.matched_rules

    def test_code_pattern(self):
        result = classify("def calculate_total(items):\n    return sum(items)")
        assert result.is_sensitive
        assert "file_content" in result.flags
        assert "code_pattern" in result.matched_rules


class TestMultipleFlags:
    def test_email_with_pii(self):
        result = classify("From: Dr. Smith\nSubject: Your account number 123456789")
        assert result.is_sensitive
        assert len(result.flags) >= 2
        assert result.confidence > 0.25

    def test_confidence_scales(self):
        result = classify(
            "From: john@example.com\n"
            "Call Dr. Smith at (555) 123-4567\n"
            "Wire transfer for $100,000.00"
        )
        assert result.confidence == 1.0
