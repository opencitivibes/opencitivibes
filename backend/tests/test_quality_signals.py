"""
Tests for Quality Signals Phase 1: Backend Aggregation.

Tests:
- VoteRepository trust distribution methods
- AnalyticsRepository weighted score methods
- QualitySignalsService aggregation
- Public quality signals endpoint
- Admin weighted score endpoints
"""

from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from models.schemas import (
    QualityCounts,
    QualitySignalsResponse,
    ScoreAnomaliesResponse,
    TrustDistribution,
    WeightedScoreResponse,
)
from repositories.vote_repository import VoteRepository
from repositories.analytics_repository import AnalyticsRepository
from services.quality_signals_service import QualitySignalsService
from services.analytics_service import AnalyticsService


# ============================================================================
# VoteRepository Tests
# ============================================================================


class TestVoteRepositoryTrustDistribution:
    """Tests for VoteRepository trust distribution methods."""

    def test_get_trust_distribution_for_idea_empty(self, db_session: Session):
        """Test trust distribution returns zeros for idea with no votes."""
        repo = VoteRepository(db_session)

        result = repo.get_trust_distribution_for_idea(99999)

        assert result["excellent"] == 0
        assert result["good"] == 0
        assert result["average"] == 0
        assert result["below_average"] == 0
        assert result["low"] == 0
        assert result["total_votes"] == 0

    def test_get_trust_distribution_batch_empty(self, db_session: Session):
        """Test batch trust distribution returns empty dict for empty list."""
        repo = VoteRepository(db_session)

        result = repo.get_trust_distribution_batch([])

        assert result == {}

    def test_get_trust_distribution_batch_no_votes(self, db_session: Session):
        """Test batch trust distribution returns zeros for ideas with no votes."""
        repo = VoteRepository(db_session)

        result = repo.get_trust_distribution_batch([99997, 99998, 99999])

        assert len(result) == 3
        for idea_id in [99997, 99998, 99999]:
            assert result[idea_id]["excellent"] == 0
            assert result[idea_id]["total_votes"] == 0

    def test_get_stakeholder_distribution_placeholder(self, db_session: Session):
        """Test stakeholder distribution returns empty dict (placeholder)."""
        repo = VoteRepository(db_session)

        result = repo.get_stakeholder_distribution_for_idea(1)

        assert result == {}


# ============================================================================
# AnalyticsRepository Tests
# ============================================================================


class TestAnalyticsRepositoryWeightedScore:
    """Tests for AnalyticsRepository weighted score methods."""

    def test_get_weighted_score_for_idea_no_votes(self, db_session: Session):
        """Test weighted score returns zeros for idea with no votes."""
        result = AnalyticsRepository.get_weighted_score_for_idea(db_session, 99999)

        assert result["weighted_score"] == 0.0
        assert result["public_score"] == 0
        assert result["divergence"] == 0.0

    def test_get_weighted_scores_batch_empty(self, db_session: Session):
        """Test batch weighted scores returns empty dict for empty list."""
        result = AnalyticsRepository.get_weighted_scores_batch(db_session, [])

        assert result == {}

    def test_get_weighted_scores_batch_no_votes(self, db_session: Session):
        """Test batch weighted scores returns zeros for ideas with no votes."""
        result = AnalyticsRepository.get_weighted_scores_batch(
            db_session, [99997, 99998, 99999]
        )

        assert len(result) == 3
        for idea_id in [99997, 99998, 99999]:
            assert result[idea_id]["weighted_score"] == 0.0
            assert result[idea_id]["public_score"] == 0
            assert result[idea_id]["divergence"] == 0.0

    def test_get_score_anomalies_empty(self, db_session: Session):
        """Test score anomalies returns empty list when no anomalies."""
        result = AnalyticsRepository.get_score_anomalies(db_session, threshold=0.3)

        # Should return empty list or list with no items above threshold
        assert isinstance(result, list)


# ============================================================================
# QualitySignalsService Tests
# ============================================================================


class TestQualitySignalsService:
    """Tests for QualitySignalsService."""

    def test_get_signals_for_idea_returns_response(self, db_session: Session):
        """Test get_signals_for_idea returns QualitySignalsResponse."""
        # This test assumes the idea may not exist, but service should handle it
        with patch.object(VoteRepository, "get_trust_distribution_for_idea") as mock_td:
            mock_td.return_value = {
                "excellent": 2,
                "good": 3,
                "average": 5,
                "below_average": 1,
                "low": 0,
                "total_votes": 11,
            }

            with patch(
                "services.quality_signals_service.VoteQualityRepository"
            ) as mock_vqr:
                mock_vqr_instance = MagicMock()
                mock_vqr_instance.get_detailed_counts_for_idea.return_value = [
                    {"quality_id": 1, "quality_key": "innovative", "count": 5}
                ]
                mock_vqr_instance.count_votes_with_qualities.return_value = 5
                mock_vqr.return_value = mock_vqr_instance

                result = QualitySignalsService.get_signals_for_idea(db_session, 1)

                assert isinstance(result, QualitySignalsResponse)
                assert result.trust_distribution.excellent == 2
                assert result.trust_distribution.total_votes == 11
                assert result.total_upvotes == 11
                assert result.votes_with_qualities == 5

    def test_get_signals_batch_empty(self, db_session: Session):
        """Test get_signals_batch returns empty dict for empty list."""
        result = QualitySignalsService.get_signals_batch(db_session, [])

        assert result == {}

    def test_get_signals_batch_returns_dict(self, db_session: Session):
        """Test get_signals_batch returns dict of responses."""
        with patch.object(VoteRepository, "get_trust_distribution_batch") as mock_td:
            mock_td.return_value = {
                1: {
                    "excellent": 1,
                    "good": 2,
                    "average": 3,
                    "below_average": 0,
                    "low": 0,
                    "total_votes": 6,
                },
                2: {
                    "excellent": 0,
                    "good": 0,
                    "average": 0,
                    "below_average": 0,
                    "low": 0,
                    "total_votes": 0,
                },
            }

            with patch(
                "services.quality_signals_service.VoteQualityRepository"
            ) as mock_vqr:
                mock_vqr_instance = MagicMock()
                mock_vqr_instance.get_counts_for_ideas_batch.return_value = {
                    1: {"counts": [], "total_votes_with_qualities": 3},
                    2: {"counts": [], "total_votes_with_qualities": 0},
                }
                mock_vqr.return_value = mock_vqr_instance

                result = QualitySignalsService.get_signals_batch(db_session, [1, 2])

                assert len(result) == 2
                assert 1 in result
                assert 2 in result
                assert isinstance(result[1], QualitySignalsResponse)


# ============================================================================
# AnalyticsService Weighted Score Tests
# ============================================================================


class TestAnalyticsServiceWeightedScore:
    """Tests for AnalyticsService weighted score methods."""

    def test_get_weighted_score_analytics(self, db_session: Session):
        """Test get_weighted_score_analytics returns correct structure."""
        with patch.object(
            AnalyticsRepository, "get_weighted_score_for_idea"
        ) as mock_ws:
            mock_ws.return_value = {
                "weighted_score": 8.5,
                "public_score": 10,
                "divergence": 0.15,
            }

            with patch.object(
                VoteRepository, "get_trust_distribution_for_idea"
            ) as mock_td:
                mock_td.return_value = {
                    "excellent": 5,
                    "good": 3,
                    "average": 2,
                    "below_average": 0,
                    "low": 0,
                    "total_votes": 10,
                }

                # Clear cache first
                AnalyticsService.invalidate_cache()

                result = AnalyticsService.get_weighted_score_analytics(db_session, 1)

                assert result["idea_id"] == 1
                assert result["public_score"] == 10
                assert result["weighted_score"] == 8.5
                assert result["divergence_percent"] == 15.0
                assert "trust_distribution" in result

    def test_get_score_anomalies(self, db_session: Session):
        """Test get_score_anomalies returns correct structure."""
        with patch.object(AnalyticsRepository, "get_score_anomalies") as mock_anom:
            mock_anom.return_value = [
                {
                    "idea_id": 1,
                    "title": "Test Idea",
                    "weighted_score": 3.0,
                    "public_score": 10,
                    "divergence_percent": 70.0,
                }
            ]

            result = AnalyticsService.get_score_anomalies(db_session, 0.3)

            assert result["threshold_percent"] == 30.0
            assert result["count"] == 1
            assert len(result["anomalies"]) == 1
            assert result["anomalies"][0]["idea_id"] == 1


# ============================================================================
# Integration Tests (require test fixtures)
# ============================================================================


class TestQualitySignalsIntegration:
    """Integration tests for quality signals endpoints."""

    def test_quality_signals_endpoint_exists(self, client, db_session):
        """Test that the quality signals endpoint exists."""
        # The endpoint should return 404 for non-existent idea
        response = client.get("/api/ideas/99999/quality-signals")
        assert response.status_code == 404

    def test_quality_signals_endpoint_with_idea(self, client, test_idea):
        """Test quality signals endpoint with existing idea."""
        response = client.get(f"/api/ideas/{test_idea.id}/quality-signals")
        assert response.status_code == 200

        data = response.json()
        assert "trust_distribution" in data
        assert "quality_counts" in data
        assert "votes_with_qualities" in data
        assert "total_upvotes" in data

    def test_admin_weighted_scores_requires_auth(self, client):
        """Test that admin weighted scores endpoint requires authentication."""
        response = client.get("/api/admin/analytics/weighted-scores/1")
        assert response.status_code == 401

    def test_admin_score_anomalies_requires_auth(self, client):
        """Test that admin score anomalies endpoint requires authentication."""
        response = client.get("/api/admin/analytics/score-anomalies")
        assert response.status_code == 401

    def test_admin_weighted_scores_with_auth(
        self, client, admin_auth_headers, test_idea
    ):
        """Test admin weighted scores endpoint with admin authentication."""
        response = client.get(
            f"/api/admin/analytics/weighted-scores/{test_idea.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "idea_id" in data
        assert "public_score" in data
        assert "weighted_score" in data
        assert "divergence_percent" in data
        assert "trust_distribution" in data

    def test_admin_score_anomalies_with_auth(self, client, admin_auth_headers):
        """Test admin score anomalies endpoint with admin authentication."""
        response = client.get(
            "/api/admin/analytics/score-anomalies",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "threshold_percent" in data
        assert "anomalies" in data
        assert "count" in data


# ============================================================================
# Schema Tests
# ============================================================================


class TestQualitySignalsSchemas:
    """Tests for quality signals Pydantic schemas."""

    def test_trust_distribution_defaults(self):
        """Test TrustDistribution has correct defaults."""
        td = TrustDistribution()

        assert td.excellent == 0
        assert td.good == 0
        assert td.average == 0
        assert td.below_average == 0
        assert td.low == 0
        assert td.total_votes == 0

    def test_trust_distribution_with_values(self):
        """Test TrustDistribution with provided values."""
        td = TrustDistribution(
            excellent=5, good=10, average=15, below_average=3, low=2, total_votes=35
        )

        assert td.excellent == 5
        assert td.total_votes == 35

    def test_quality_signals_response(self):
        """Test QualitySignalsResponse structure."""
        response = QualitySignalsResponse(
            trust_distribution=TrustDistribution(total_votes=10),
            quality_counts=QualityCounts(),
            votes_with_qualities=5,
            total_upvotes=10,
        )

        assert response.total_upvotes == 10
        assert response.votes_with_qualities == 5

    def test_weighted_score_response(self):
        """Test WeightedScoreResponse structure."""
        response = WeightedScoreResponse(
            idea_id=1,
            public_score=10,
            weighted_score=8.5,
            divergence_percent=15.0,
            trust_distribution=TrustDistribution(),
        )

        assert response.idea_id == 1
        assert response.divergence_percent == 15.0

    def test_score_anomalies_response(self):
        """Test ScoreAnomaliesResponse structure."""
        response = ScoreAnomaliesResponse(threshold_percent=30.0, anomalies=[], count=0)

        assert response.threshold_percent == 30.0
        assert response.count == 0
