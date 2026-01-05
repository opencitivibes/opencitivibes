"""
Similar Ideas Detection Service

Finds similar ideas to prevent duplicates.
Optimized to use database-level filtering and batch queries.
"""

import re
from typing import Any

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from services.config_service import get_config


def _get_entity_stopwords() -> set[str]:
    """Get instance-specific stopwords (entity names that shouldn't affect similarity).

    Returns:
        Set of lowercased entity names from the platform configuration.
    """
    config = get_config()
    stopwords: set[str] = set()

    # Add entity name in all supported locales
    for locale in config.localization.supported_locales:
        name = config.instance.entity.name.get(locale, "").lower()
        if name:
            stopwords.add(name)

    # Add region names if present
    if config.instance.entity.region:
        for locale in config.localization.supported_locales:
            region = config.instance.entity.region.get(locale, "").lower()
            if region:
                stopwords.add(region)

    # Add instance name variants (e.g., "idées pour montréal")
    for locale in config.localization.supported_locales:
        instance_name = config.instance.name.get(locale, "").lower()
        if instance_name:
            # Add both full name and individual words
            stopwords.add(instance_name)
            for word in instance_name.split():
                if len(word) > 2:
                    stopwords.add(word)

    return stopwords


class SimilarIdeasService:
    """Service for detecting similar ideas."""

    # Common stop words to ignore in similarity calculation
    STOP_WORDS_EN = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "were",
        "been",
        "be",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
    }

    STOP_WORDS_FR = {
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "et",
        "ou",
        "mais",
        "dans",
        "sur",
        "à",
        "pour",
        "de",
        "avec",
        "par",
        "comme",
        "est",
        "sont",
        "était",
        "étaient",
        "été",
        "être",
        "avoir",
        "a",
        "ont",
        "avait",
        "avaient",
        "faire",
        "fait",
        "ce",
        "cet",
        "cette",
        "ces",
        "je",
        "tu",
        "il",
        "elle",
        "nous",
        "vous",
        "ils",
        "elles",
    }

    # Base domain-specific stop words (non-entity specific)
    BASE_DOMAIN_STOP_WORDS = {
        "ville",
        "city",
        "idée",
        "idea",
        "projet",
        "project",
    }

    def __init__(self) -> None:
        """Initialize the similar ideas service."""
        # Combine base domain stopwords with entity-specific ones from config
        self._domain_stop_words = self.BASE_DOMAIN_STOP_WORDS | _get_entity_stopwords()

    def extract_keywords(self, text: str, language: str = "en") -> set[str]:
        """
        Extract keywords from text, removing stop words.

        Args:
            text: Text to process
            language: Language code ('en' or 'fr')

        Returns:
            Set of keywords
        """
        if not text:
            return set()

        # Select stop words based on language
        stop_words = self.STOP_WORDS_FR if language == "fr" else self.STOP_WORDS_EN
        all_stop_words = stop_words | self._domain_stop_words

        # Convert to lowercase and extract words
        words = re.findall(r"\b\w+\b", text.lower())

        # Filter out stop words and short words
        keywords = {
            word for word in words if word not in all_stop_words and len(word) > 2
        }

        return keywords

    def calculate_similarity(
        self, title1: str, desc1: str, title2: str, desc2: str, language: str = "en"
    ) -> float:
        """
        Calculate similarity between two ideas using Jaccard similarity.

        Args:
            title1: First idea title
            desc1: First idea description
            title2: Second idea title
            desc2: Second idea description
            language: Language code

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Extract keywords from both ideas
        # Weight title more heavily than description
        keywords1_title = self.extract_keywords(title1, language)
        keywords1_desc = self.extract_keywords(desc1, language)
        keywords1 = keywords1_title.union(keywords1_desc)
        # Give extra weight to title words
        keywords1.update(keywords1_title)  # Add title words twice

        keywords2_title = self.extract_keywords(title2, language)
        keywords2_desc = self.extract_keywords(desc2, language)
        keywords2 = keywords2_title.union(keywords2_desc)
        # Give extra weight to title words
        keywords2.update(keywords2_title)  # Add title words twice

        if not keywords1 or not keywords2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(keywords1.intersection(keywords2))
        union = len(keywords1.union(keywords2))

        similarity = intersection / union if union > 0 else 0.0

        return similarity

    def _build_keyword_conditions(
        self, keywords: set[str], max_keywords: int = 10
    ) -> list[Any]:
        """
        Build OR conditions for keyword matching in database.

        Args:
            keywords: Set of keywords to match
            max_keywords: Maximum number of keywords to use

        Returns:
            List of SQLAlchemy filter conditions
        """
        conditions = []
        # Limit keywords to prevent excessive OR conditions
        limited_keywords = list(keywords)[:max_keywords]

        for keyword in limited_keywords:
            # Use ilike for case-insensitive matching
            conditions.append(db_models.Idea.title.ilike(f"%{keyword}%"))
            conditions.append(db_models.Idea.description.ilike(f"%{keyword}%"))

        return conditions

    def _fetch_vote_counts_batch(
        self, db: Session, idea_ids: list[int]
    ) -> dict[int, dict[str, int]]:
        """
        Batch fetch vote counts for multiple ideas.

        Args:
            db: Database session
            idea_ids: List of idea IDs

        Returns:
            Dict mapping idea_id to {upvotes, downvotes, score}
        """
        from repositories.vote_repository import VoteRepository

        if not idea_ids:
            return {}

        vote_repo = VoteRepository(db)
        return vote_repo.get_vote_counts_batch(idea_ids)

    def find_similar_ideas(
        self,
        title: str,
        description: str,
        db: Session,
        category_id: int | None = None,
        threshold: float = 0.3,
        limit: int = 5,
        language: str = "en",
    ) -> list[dict[str, Any]]:
        """
        Find similar approved ideas based on title and description.

        Uses database-level filtering and batch queries for performance.

        Args:
            title: Idea title to compare
            description: Idea description to compare
            db: Database session
            category_id: Optional category filter
            threshold: Minimum similarity score (0.0 to 1.0)
            limit: Maximum number of results
            language: Language code

        Returns:
            List of similar ideas with similarity scores
        """
        from repositories.idea_repository import IdeaRepository

        # Extract keywords from input
        text = f"{title} {description}"
        keywords = self.extract_keywords(text, language)

        if not keywords:
            return []

        # Fetch more candidates than needed for scoring
        # (some may fall below threshold after similarity calculation)
        candidate_limit = limit * 5

        idea_repo = IdeaRepository(db)
        ideas = idea_repo.search_by_keywords(keywords, category_id, candidate_limit)

        if not ideas:
            return []

        # Calculate similarity for filtered candidates
        similar_candidates = []
        for idea in ideas:
            similarity = self.calculate_similarity(
                title, description, idea.title, idea.description, language
            )

            if similarity >= threshold:
                similar_candidates.append({"idea": idea, "similarity": similarity})

        if not similar_candidates:
            return []

        # Batch fetch vote counts (eliminates N+1 queries)
        idea_ids = [c["idea"].id for c in similar_candidates]
        vote_counts = self._fetch_vote_counts_batch(db, idea_ids)

        # Build result with scores
        similar_ideas = []
        for candidate in similar_candidates:
            idea = candidate["idea"]
            votes = vote_counts.get(idea.id, {"upvotes": 0, "downvotes": 0, "score": 0})

            similar_ideas.append(
                {
                    "id": idea.id,
                    "title": idea.title,
                    "description": idea.description[:200],  # Truncate for preview
                    "score": votes["score"],
                    "similarity_score": round(candidate["similarity"], 2),
                }
            )

        # Sort by similarity score (descending)
        similar_ideas.sort(key=lambda x: x["similarity_score"], reverse=True)

        return similar_ideas[:limit]
