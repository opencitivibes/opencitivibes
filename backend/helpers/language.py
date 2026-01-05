"""Language utility functions."""


def parse_accept_language(accept_language: str) -> str:
    """
    Parse Accept-Language header to extract preferred language.

    Handles formats like:
    - "fr" -> "fr"
    - "fr-CA" -> "fr"
    - "fr-CA,fr;q=0.9,en;q=0.8" -> "fr"
    - "en-US,en;q=0.9" -> "en"

    Returns "fr" as default for invalid/unknown languages.
    """
    if not accept_language:
        return "fr"

    # Split by comma and take the first (highest priority) language
    primary = accept_language.split(",")[0].strip()

    # Extract language code (before any dash or semicolon)
    lang = primary.split("-")[0].split(";")[0].strip().lower()

    # Only accept fr or en, default to fr
    return lang if lang in ("fr", "en") else "fr"
