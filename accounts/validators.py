import re

from django.conf import settings
from django.core.exceptions import ValidationError


class LetterAndNumberValidator:
    """BR-03: a password must contain at least one letter and one number."""

    def validate(self, password, user=None):
        if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            raise ValidationError(
                "Your password must contain at least one letter and one number.",
                code="password_no_letter_number",
            )

    def get_help_text(self):
        return "Your password must contain at least one letter and one number."


def validate_institutional_email(email):
    """BR-01: the email must belong to the CIT-U domain (when one is configured)."""
    domain = getattr(settings, "ALLOWED_EMAIL_DOMAIN", "")
    if domain and not email.lower().endswith("@" + domain.lower()):
        raise ValidationError(f"Please use your CIT-U email address (ending in @{domain}).")
