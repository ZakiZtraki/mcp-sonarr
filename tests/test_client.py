"""Tests for Sonarr API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_sonarr.sonarr_client import SonarrClient, SonarrConfig


@pytest.fixture
def config():
    """Create test configuration."""
    return SonarrConfig(
        url="https://sonarr.example.com",
        api_key="test-api-key",
    )


@pytest.fixture
def client(config):
    """Create test client."""
    return SonarrClient(config)


class TestSonarrClient:
    """Tests for SonarrClient."""

    def test_init(self, client, config):
        """Test client initialization."""
        assert client.base_url == "https://sonarr.example.com"
        assert client.headers["X-Api-Key"] == "test-api-key"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from URL."""
        config = SonarrConfig(
            url="https://sonarr.example.com/",
            api_key="test-key",
        )
        client = SonarrClient(config)
        assert client.base_url == "https://sonarr.example.com"

    @pytest.mark.asyncio
    async def test_get_system_status(self, client):
        """Test get_system_status method."""
        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "version": "4.0.0.0",
                "buildTime": "2024-01-01T00:00:00Z",
            }

            result = await client.get_system_status()

            mock_get.assert_called_once_with("system/status")
            assert result["version"] == "4.0.0.0"

    @pytest.mark.asyncio
    async def test_get_all_series(self, client):
        """Test get_all_series method."""
        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"id": 1, "title": "Series 1"},
                {"id": 2, "title": "Series 2"},
            ]

            result = await client.get_all_series()

            mock_get.assert_called_once_with("series")
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_series(self, client):
        """Test search_series method."""
        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"tvdbId": 12345, "title": "Test Series"},
            ]

            result = await client.search_series("Test Series")

            mock_get.assert_called_once_with("series/lookup", params={"term": "Test Series"})
            assert result[0]["tvdbId"] == 12345

    @pytest.mark.asyncio
    async def test_get_queue(self, client):
        """Test get_queue method."""
        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "totalRecords": 5,
                "records": [],
            }

            result = await client.get_queue(page=1, page_size=10)

            assert result["totalRecords"] == 5

    @pytest.mark.asyncio
    async def test_get_calendar(self, client):
        """Test get_calendar method."""
        with patch.object(client, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"id": 1, "title": "Episode 1"},
            ]

            result = await client.get_calendar()

            assert len(result) == 1


class TestSonarrConfig:
    """Tests for SonarrConfig."""

    def test_config_creation(self):
        """Test config creation with required fields."""
        config = SonarrConfig(
            url="https://sonarr.example.com",
            api_key="test-key",
        )
        assert config.url == "https://sonarr.example.com"
        assert config.api_key == "test-key"
        assert config.timeout == 30.0

    def test_config_custom_timeout(self):
        """Test config with custom timeout."""
        config = SonarrConfig(
            url="https://sonarr.example.com",
            api_key="test-key",
            timeout=60.0,
        )
        assert config.timeout == 60.0
