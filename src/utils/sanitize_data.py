import re
import logging

import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = spacy.blank("en")

PROFANITY_PATTERNS = [
    r"\b(?:damn|hell|crap|idiot|stupid|trash|dumb)\b",
    r"\b(?:f+u+c+k|f\s*u\s*c\s*k|sh\s*t|b\s*i\s*t\s*c\s*h|a\s*s\s*s)\b",
]

logger = logging.getLogger(__name__)


class SanitizationError(ValueError):
    """Raised when user input cannot be safely sanitized."""


def censor_profanity(text: str) -> str:
    """Replace common profanities with a neutral mask."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    try:
        censored = text
        for pattern in PROFANITY_PATTERNS:
            censored = re.sub(pattern, "[REDACTED]", censored, flags=re.IGNORECASE)
        return censored
    except Exception as exc:
        logger.exception("Failed to censor user input")
        raise SanitizationError("Unable to sanitize user input.") from exc


def sanitize_all_input(text: str) -> str:
    """
    Completely sanitizes unstructured text by masking Names, Addresses,
    SINs, Cards, Phones, and censoring harmful language.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        raise SanitizationError("Input must be a string.")

    try:
        text = censor_profanity(text)

        # 2. Mask Numerical PII using Regular Expressions
        sin_pattern = r"\b\d{3}[- ]?\d{3}[- ]?\d{3}\b"
        text = re.sub(sin_pattern, "[REDACTED_SIN]", text)

        card_pattern = r"\b(?:\d[ -]*?){13,19}\b"
        text = re.sub(card_pattern, "[REDACTED_CARD]", text)

        phone_pattern = r"\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b"
        text = re.sub(phone_pattern, "[REDACTED_PHONE]", text)

        # 3. Mask Names and Addresses using SpaCy NLP
        doc = nlp(text)
        ents_to_redact = []

        for ent in doc.ents:
            if ent.label_ in ["PERSON", "GPE", "FAC", "LOC"]:
                ents_to_redact.append((ent.start_char, ent.end_char, ent.label_))

        for start, end, label in sorted(ents_to_redact, key=lambda x: x[0], reverse=True):
            mask_tag = "[REDACTED_NAME]" if label == "PERSON" else "[REDACTED_ADDRESS]"
            text = text[:start] + mask_tag + text[end:]

        text = re.sub(r"\s+", " ", text).strip()
        return text
    except SanitizationError:
        raise
    except Exception as exc:
        logger.exception("Failed to sanitize user input")
        raise SanitizationError("Unable to sanitize user input.") from exc
