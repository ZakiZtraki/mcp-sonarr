"""Tests for Sonarr API client and MCP server tools."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_sonarr.sonarr_client import SonarrClient, SonarrConfig
from mcp_sonarr.server import _execute_tool


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


class TestSeriesTools:
    """Tests for series-related MCP tools."""

    @pytest.fixture
    def mock_series_data(self):
        """Sample series data as returned by Sonarr API."""
        return [
            {
                "id": 1,
                "title": "Breaking Bad",
                "year": 2008,
                "status": "ended",
                "monitored": True,
                "seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}, {"seasonNumber": 3}],
                "statistics": {
                    "episodeCount": 62,
                    "episodeFileCount": 62,
                    "percentOfEpisodes": 100,
                    "sizeOnDisk": 50000000000,
                },
                "added": "2020-01-15T10:00:00Z",
            },
            {
                "id": 2,
                "title": "Game of Thrones",
                "year": 2011,
                "status": "ended",
                "monitored": False,
                "seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}],
                "statistics": {
                    "episodeCount": 73,
                    "episodeFileCount": 73,
                    "percentOfEpisodes": 100,
                    "sizeOnDisk": 80000000000,
                },
                "added": "2019-05-20T08:30:00Z",
            },
            {
                "id": 3,
                "title": "The Mandalorian",
                "year": 2019,
                "status": "continuing",
                "monitored": True,
                "seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}, {"seasonNumber": 3}],
                "statistics": {
                    "episodeCount": 24,
                    "episodeFileCount": 24,
                    "percentOfEpisodes": 100,
                    "sizeOnDisk": 30000000000,
                },
                "added": "2021-03-10T14:20:00Z",
            },
            {
                "id": 4,
                "title": "Stranger Things",
                "year": 2016,
                "status": "continuing",
                "monitored": True,
                "seasons": [{"seasonNumber": 1}, {"seasonNumber": 2}],
                "statistics": {
                    "episodeCount": 34,
                    "episodeFileCount": 34,
                    "percentOfEpisodes": 100,
                    "sizeOnDisk": 45000000000,
                },
                "added": "2020-07-05T16:45:00Z",
            },
        ]

    @pytest.mark.asyncio
    async def test_get_all_series_returns_object_with_items_array(self, mock_series_data):
        """Test that sonarr_get_all_series returns an object with 'items' array and 'total'."""
        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=mock_series_data)

        result = await _execute_tool(mock_client, "sonarr_get_all_series", {})

        # Verify response is an object, not a raw array
        assert isinstance(result, dict), "Response should be a dict, not a list"
        assert "items" in result, "Response should contain 'items' key"
        assert "total" in result, "Response should contain 'total' key"

        # Verify items is an array
        assert isinstance(result["items"], list), "'items' should be a list"

        # Verify all series are returned
        assert len(result["items"]) == 4, "Should return all 4 series"
        assert result["total"] == 4, "Total should be 4"

    @pytest.mark.asyncio
    async def test_get_all_series_items_have_correct_structure(self, mock_series_data):
        """Test that each item in the response has the expected fields."""
        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=mock_series_data)

        result = await _execute_tool(mock_client, "sonarr_get_all_series", {})

        for item in result["items"]:
            # Verify all expected fields exist
            assert "id" in item
            assert "title" in item
            assert "year" in item
            assert "status" in item
            assert "monitored" in item
            assert "seasons" in item
            assert "episodeCount" in item
            assert "episodeFileCount" in item
            assert "percentComplete" in item
            assert "sizeOnDisk" in item
            assert "added" in item

    @pytest.mark.asyncio
    async def test_list_series_filter_by_status_ended(self, mock_series_data):
        """Test filtering series by status='ended'."""
        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=mock_series_data)

        result = await _execute_tool(mock_client, "sonarr_list_series", {"status": "ended"})

        assert result["total"] == 2, "Should return 2 ended series"
        assert all(s["status"] == "ended" for s in result["items"])

    @pytest.mark.asyncio
    async def test_list_series_filter_by_monitored_true(self, mock_series_data):
        """Test filtering series by monitored=true."""
        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=mock_series_data)

        result = await _execute_tool(mock_client, "sonarr_list_series", {"monitored": True})

        assert result["total"] == 3, "Should return 3 monitored series"
        assert all(s["monitored"] is True for s in result["items"])

    @pytest.mark.asyncio
    async def test_list_series_filter_ended_and_monitored(self, mock_series_data):
        """Test filtering series by status='ended' AND monitored=true."""
        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=mock_series_data)

        result = await _execute_tool(
            mock_client, "sonarr_list_series", {"status": "ended", "monitored": True}
        )

        # Only Breaking Bad matches: ended AND monitored
        assert result["total"] == 1, "Should return 1 series (ended + monitored)"
        assert result["items"][0]["title"] == "Breaking Bad"

    @pytest.mark.asyncio
    async def test_list_series_filter_by_title_contains(self, mock_series_data):
        """Test filtering series by title substring."""
        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=mock_series_data)

        # Search for "man" which appears in "The Mandalorian"
        result = await _execute_tool(mock_client, "sonarr_list_series", {"title_contains": "man"})
        assert result["total"] == 1
        assert result["items"][0]["title"] == "The Mandalorian"

        # Search for "stranger" (case-insensitive)
        result2 = await _execute_tool(
            mock_client, "sonarr_list_series", {"title_contains": "STRANGER"}
        )
        assert result2["total"] == 1
        assert result2["items"][0]["title"] == "Stranger Things"

    @pytest.mark.asyncio
    async def test_list_series_pagination(self, mock_series_data):
        """Test pagination works correctly."""
        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=mock_series_data)

        # Get first page with page_size=2
        result = await _execute_tool(mock_client, "sonarr_list_series", {"page": 1, "page_size": 2})

        assert result["total"] == 4, "Total should still be 4"
        assert len(result["items"]) == 2, "Page should have 2 items"
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert result["total_pages"] == 2

        # Get second page
        result2 = await _execute_tool(
            mock_client, "sonarr_list_series", {"page": 2, "page_size": 2}
        )

        assert len(result2["items"]) == 2, "Second page should have 2 items"
        assert result2["page"] == 2

    @pytest.mark.asyncio
    async def test_list_series_sort_by_year_desc(self, mock_series_data):
        """Test sorting by year in descending order."""
        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=mock_series_data)

        result = await _execute_tool(
            mock_client, "sonarr_list_series", {"sort_by": "year", "sort_order": "desc"}
        )

        years = [s["year"] for s in result["items"]]
        assert years == sorted(years, reverse=True), "Should be sorted by year descending"

    @pytest.mark.asyncio
    async def test_list_series_filters_applied_metadata(self, mock_series_data):
        """Test that filters_applied metadata is included in response."""
        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=mock_series_data)

        result = await _execute_tool(
            mock_client,
            "sonarr_list_series",
            {"status": "ended", "monitored": True, "title_contains": "bad"},
        )

        assert "filters_applied" in result
        assert result["filters_applied"]["status"] == "ended"
        assert result["filters_applied"]["monitored"] is True
        assert result["filters_applied"]["title_contains"] == "bad"

    @pytest.mark.asyncio
    async def test_large_library_not_truncated(self):
        """Test that large libraries are fully returned without truncation."""
        # Create a large mock library (200 series)
        large_series = [
            {
                "id": i,
                "title": f"Series {i}",
                "year": 2000 + (i % 25),
                "status": "ended" if i % 2 == 0 else "continuing",
                "monitored": i % 3 != 0,
                "seasons": [{"seasonNumber": 1}],
                "statistics": {
                    "episodeCount": 10,
                    "episodeFileCount": 10,
                    "percentOfEpisodes": 100,
                    "sizeOnDisk": 1000000000,
                },
                "added": f"2020-01-{(i % 28) + 1:02d}T00:00:00Z",
            }
            for i in range(1, 201)
        ]

        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=large_series)

        result = await _execute_tool(mock_client, "sonarr_get_all_series", {})

        assert result["total"] == 200, "Should return all 200 series"
        assert len(result["items"]) == 200, "Items array should have 200 series"

    @pytest.mark.asyncio
    async def test_list_series_pagination_max_page_size(self):
        """Test that page_size is capped at 500."""
        large_series = [
            {
                "id": i,
                "title": f"Series {i}",
                "year": 2020,
                "status": "continuing",
                "monitored": True,
                "seasons": [],
                "statistics": {},
                "added": "2020-01-01T00:00:00Z",
            }
            for i in range(1, 1001)
        ]

        mock_client = MagicMock()
        mock_client.get_all_series = AsyncMock(return_value=large_series)

        result = await _execute_tool(mock_client, "sonarr_list_series", {"page_size": 1000})

        # Should be capped at 500
        assert result["page_size"] == 500
        assert len(result["items"]) == 500
