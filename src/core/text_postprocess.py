"""
Text post-processing engine for Dictatly.
Provides dictionary-based word/phrase replacements and smart punctuation formatting.
"""

import re
from typing import Dict

def apply_vocabulary(text: str, replacements: Dict[str, str]) -> str:
    """
    Applies custom word and term replacements (case-insensitive, whole words/phrases).
    Example: 'пайтон' -> 'Python', 'гитхаб' -> 'GitHub'.
    """
    if not text or not replacements:
        return text

    for src_term, target_term in replacements.items():
        src = src_term.strip()
        target = target_term.strip()
        if not src or not target:
            continue

        # Use boundary check that handles both Cyrillic and Latin characters
        pattern = rf"(?<!\w){re.escape(src)}(?!\w)"
        text = re.sub(pattern, target, text, flags=re.IGNORECASE | re.UNICODE)

    return text

def format_smart_punctuation(text: str, enabled: bool = True) -> str:
    """
    Normalizes spacing, capitalizes initial letter, and cleans up transcription formatting.
    """
    if not text:
        return ""

    if not enabled:
        return re.sub(r"[ \t]+", " ", text).strip()

    cleaned = text.strip()
    if not cleaned:
        return ""

    # Capitalize the first character of the utterance if it is lowercase
    if cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]

    # Remove whitespace before punctuation marks
    cleaned = re.sub(r"\s+([,.!?:;])", r"\1", cleaned)

    # Ensure space after punctuation when followed directly by letters or numbers,
    # while preserving decimal numbers (3.14, 1,5), clock times (12:30), and ASCII domains (google.com)
    def _punct_spacer(m):
        punct = m.group(1)
        next_char = m.group(2)
        prev_char = m.string[m.start() - 1] if m.start() > 0 else ""

        # Protect decimal numbers and digit separators: 3.14, 1,5, 1,000
        if punct in ".," and prev_char.isdigit() and next_char.isdigit():
            return m.group(0)

        # Protect clock times: 12:30
        if punct == ":" and prev_char.isdigit() and next_char.isdigit():
            return m.group(0)

        # Protect ASCII domains and filenames: google.com, test.py
        if punct == "." and prev_char.isascii() and prev_char.isalnum() and next_char.isascii() and next_char.islower():
            return m.group(0)

        return f"{punct} {next_char}"

    cleaned = re.sub(r"([,.!?:;])([A-Za-zА-Яа-яЁё0-9])", _punct_spacer, cleaned)

    # Capitalize first letter following sentence-ending punctuation
    cleaned = re.sub(r"([.!?]\s+)([a-zа-яё])", lambda m: m.group(1) + m.group(2).upper(), cleaned)

    # Collapse multiple consecutive whitespace characters into a single space
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

    return cleaned
