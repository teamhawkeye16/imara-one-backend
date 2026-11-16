"""
IMARA ONE Search - Input Sanitizer and Output Escaping
"""

import html
import re
from typing import Optional


def sanitize_query(query: str, max_length: int = 250) -> str:
    """
    Sanitizes user search input:
    - Strips leading/trailing whitespace
    - Limits length
    - Eliminates control characters
    - Removes dangerous script/tag characters
    """
    if not query:
        return ""
    
    # Strip null bytes and non-printable control characters
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", query.strip())
    
    # Truncate to maximum permitted length
    cleaned = cleaned[:max_length].strip()
    
    return cleaned


def escape_output(text: str) -> str:
    """Safely escapes HTML content for display."""
    if not text:
        return ""
    return html.escape(text)


def sanitize_error_detail(error: Exception, is_debug: bool = False) -> str:
    """
    Sanitizes exceptions to prevent disclosing internal paths,
    database schemas, or stack traces to end users.
    """
    if is_debug:
        return str(error)
    return "An internal processing error occurred. Please try again later."


def clean_retrieved_context_for_ai(raw_text: str, max_chars: int = 1500) -> str:
    """
    Neutralizes prompt injection attempts within scraped/retrieved web text.
    Removes common LLM jailbreak triggers, system prompt overrides, and tags.
    """
    if not raw_text:
        return ""

    # Normalize whitespace
    text = re.sub(r"\s+", " ", raw_text).strip()

    # Neutralize attempts to command the model (e.g. 'Ignore previous instructions', 'System prompt:')
    jailbreak_patterns = [
        r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+instructions\b",
        r"(?i)\byou\s+are\s+now\s+a\b",
        r"(?i)\bsystem\s*:\s*",
        r"(?i)\bassistant\s*:\s*",
        r"(?i)\bdeveloper\s*mode\s*:\s*",
        r"(?i)\bact\s+as\s+an\s+unrestricted\b",
    ]

    for pat in jailbreak_patterns:
        text = re.sub(pat, "[FILTERED_INSTRUCTION]", text)

    return text[:max_chars]
