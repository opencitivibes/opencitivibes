"""
Content Validation Service

Handles offensive word detection in user-generated content.
"""

from typing import List, Set
import re


class ContentValidationService:
    """Service for validating user-generated content."""

    # Offensive words lists (expandable)
    OFFENSIVE_WORDS_EN: Set[str] = {
        # Common offensive terms in English
        "spam",
        "scam",
        "fraud",
        "fake",
        # Add more as needed - keeping this minimal for demonstration
    }

    OFFENSIVE_WORDS_FR: Set[str] = {
        # Common offensive terms in French
        "spam",
        "arnaque",
        "fraude",
        "faux",
        # Add more as needed - keeping this minimal for demonstration
    }

    def __init__(self):
        """Initialize the content validation service."""
        pass

    def validate_content(
        self, text: str, language: str = "en"
    ) -> tuple[bool, List[str]]:
        """
        Validate content for offensive words.

        Args:
            text: The text content to validate
            language: Language code ('en' or 'fr')

        Returns:
            Tuple of (is_valid, list_of_offensive_words_found)
        """
        if not text:
            return True, []

        # Select appropriate word list
        offensive_words = (
            self.OFFENSIVE_WORDS_FR if language == "fr" else self.OFFENSIVE_WORDS_EN
        )

        # Convert text to lowercase and split into words
        # Remove punctuation for matching
        words = re.findall(r"\b\w+\b", text.lower())

        # Find offensive words
        found_offensive = [word for word in words if word in offensive_words]

        is_valid = len(found_offensive) == 0

        return is_valid, found_offensive

    def validate_idea_content(
        self, title: str, description: str, language: str = "en"
    ) -> tuple[bool, List[str], str]:
        """
        Validate both title and description of an idea.

        Args:
            title: Idea title
            description: Idea description
            language: Language code

        Returns:
            Tuple of (is_valid, offensive_words, message)
        """
        # Validate title
        title_valid, title_offensive = self.validate_content(title, language)

        # Validate description
        desc_valid, desc_offensive = self.validate_content(description, language)

        # Combine results
        all_offensive = list(set(title_offensive + desc_offensive))
        is_valid = title_valid and desc_valid

        if not is_valid:
            if language == "fr":
                message = f"Contenu inapproprié détecté: {', '.join(all_offensive)}"
            else:
                message = f"Inappropriate content detected: {', '.join(all_offensive)}"
        else:
            message = "Content is valid"

        return is_valid, all_offensive, message

    @classmethod
    def add_offensive_word(cls, word: str, language: str = "en"):
        """
        Add a word to the offensive words list.

        Args:
            word: The word to add
            language: Language code ('en' or 'fr')
        """
        word = word.lower().strip()
        if language == "fr":
            cls.OFFENSIVE_WORDS_FR.add(word)
        else:
            cls.OFFENSIVE_WORDS_EN.add(word)

    @classmethod
    def remove_offensive_word(cls, word: str, language: str = "en"):
        """
        Remove a word from the offensive words list.

        Args:
            word: The word to remove
            language: Language code ('en' or 'fr')
        """
        word = word.lower().strip()
        if language == "fr":
            cls.OFFENSIVE_WORDS_FR.discard(word)
        else:
            cls.OFFENSIVE_WORDS_EN.discard(word)
