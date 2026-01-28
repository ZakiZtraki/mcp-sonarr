"""Sonarr API Client - Wrapper for Sonarr v3/v4 API."""

import httpx
from typing import Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel


class SonarrConfig(BaseModel):
    """Configuration for Sonarr connection."""

    url: str
    api_key: str
    timeout: float = 30.0


class SonarrClient:
    """Client for interacting with Sonarr API."""

    def __init__(self, config: SonarrConfig):
        self.config = config
        self.base_url = config.url.rstrip("/")
        self.headers = {
            "X-Api-Key": config.api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> Any:
        """Make an HTTP request to Sonarr API."""
        url = f"{self.base_url}/api/v3/{endpoint}"

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
            )
            response.raise_for_status()

            if response.status_code == 204:
                return None
            return response.json()

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """GET request to Sonarr API."""
        return await self._request("GET", endpoint, params=params)

    async def _post(self, endpoint: str, json_data: Optional[dict] = None) -> Any:
        """POST request to Sonarr API."""
        return await self._request("POST", endpoint, json_data=json_data)

    async def _put(self, endpoint: str, json_data: Optional[dict] = None) -> Any:
        """PUT request to Sonarr API."""
        return await self._request("PUT", endpoint, json_data=json_data)

    async def _delete(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """DELETE request to Sonarr API."""
        return await self._request("DELETE", endpoint, params=params)

    # ==================== System ====================

    async def get_system_status(self) -> dict:
        """Get Sonarr system status."""
        return await self._get("system/status")

    async def get_health(self) -> list:
        """Get health check results."""
        return await self._get("health")

    async def get_disk_space(self) -> list:
        """Get disk space information for root folders."""
        return await self._get("diskspace")

    async def get_root_folders(self) -> list:
        """Get configured root folders."""
        return await self._get("rootfolder")

    async def get_quality_profiles(self) -> list:
        """Get available quality profiles."""
        return await self._get("qualityprofile")

    async def get_language_profiles(self) -> list:
        """Get available language profiles."""
        return await self._get("languageprofile")

    async def get_tags(self) -> list:
        """Get all tags."""
        return await self._get("tag")

    # ==================== Series ====================

    async def get_all_series(self) -> list:
        """Get all series in the library."""
        return await self._get("series")

    async def get_series(self, series_id: int) -> dict:
        """Get a specific series by ID."""
        return await self._get(f"series/{series_id}")

    async def search_series(self, term: str) -> list:
        """Search for series to add (from TVDB/TMDB)."""
        return await self._get("series/lookup", params={"term": term})

    async def add_series(
        self,
        tvdb_id: int,
        title: str,
        quality_profile_id: int,
        root_folder_path: str,
        monitored: bool = True,
        season_folder: bool = True,
        search_for_missing: bool = True,
        tags: Optional[list[int]] = None,
    ) -> dict:
        """Add a new series to the library."""
        # First lookup the series to get full details
        lookup_results = await self._get("series/lookup", params={"term": f"tvdb:{tvdb_id}"})
        if not lookup_results:
            raise ValueError(f"Series with TVDB ID {tvdb_id} not found")

        series_data = lookup_results[0]
        series_data.update(
            {
                "qualityProfileId": quality_profile_id,
                "rootFolderPath": root_folder_path,
                "monitored": monitored,
                "seasonFolder": season_folder,
                "tags": tags or [],
                "addOptions": {
                    "searchForMissingEpisodes": search_for_missing,
                },
            }
        )

        return await self._post("series", json_data=series_data)

    async def update_series(self, series_id: int, series_data: dict) -> dict:
        """Update a series."""
        return await self._put(f"series/{series_id}", json_data=series_data)

    async def delete_series(
        self,
        series_id: int,
        delete_files: bool = False,
        add_import_list_exclusion: bool = False,
    ) -> None:
        """Delete a series from the library."""
        params = {
            "deleteFiles": str(delete_files).lower(),
            "addImportListExclusion": str(add_import_list_exclusion).lower(),
        }
        await self._delete(f"series/{series_id}", params=params)

    # ==================== Episodes ====================

    async def get_episodes(self, series_id: int) -> list:
        """Get all episodes for a series."""
        return await self._get("episode", params={"seriesId": series_id})

    async def get_episode(self, episode_id: int) -> dict:
        """Get a specific episode by ID."""
        return await self._get(f"episode/{episode_id}")

    async def get_episode_files(self, series_id: int) -> list:
        """Get episode files for a series."""
        return await self._get("episodefile", params={"seriesId": series_id})

    async def delete_episode_file(self, episode_file_id: int) -> None:
        """Delete an episode file."""
        await self._delete(f"episodefile/{episode_file_id}")

    # ==================== Calendar ====================

    async def get_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_series: bool = True,
        include_episode_file: bool = False,
    ) -> list:
        """Get upcoming episodes from the calendar."""
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if not end_date:
            end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        params = {
            "start": start_date,
            "end": end_date,
            "includeSeries": str(include_series).lower(),
            "includeEpisodeFile": str(include_episode_file).lower(),
        }
        return await self._get("calendar", params=params)

    # ==================== Queue ====================

    async def get_queue(
        self,
        page: int = 1,
        page_size: int = 20,
        include_series: bool = True,
        include_episode: bool = True,
    ) -> dict:
        """Get current download queue."""
        params = {
            "page": page,
            "pageSize": page_size,
            "includeSeries": str(include_series).lower(),
            "includeEpisode": str(include_episode).lower(),
        }
        return await self._get("queue", params=params)

    async def delete_queue_item(
        self,
        queue_id: int,
        remove_from_client: bool = True,
        blocklist: bool = False,
    ) -> None:
        """Remove an item from the download queue."""
        params = {
            "removeFromClient": str(remove_from_client).lower(),
            "blocklist": str(blocklist).lower(),
        }
        await self._delete(f"queue/{queue_id}", params=params)

    # ==================== History ====================

    async def get_history(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_key: str = "date",
        sort_direction: str = "descending",
        include_series: bool = True,
        include_episode: bool = True,
    ) -> dict:
        """Get download history."""
        params = {
            "page": page,
            "pageSize": page_size,
            "sortKey": sort_key,
            "sortDirection": sort_direction,
            "includeSeries": str(include_series).lower(),
            "includeEpisode": str(include_episode).lower(),
        }
        return await self._get("history", params=params)

    # ==================== Wanted/Missing ====================

    async def get_wanted_missing(
        self,
        page: int = 1,
        page_size: int = 20,
        include_series: bool = True,
        monitored: bool = True,
    ) -> dict:
        """Get wanted/missing episodes."""
        params = {
            "page": page,
            "pageSize": page_size,
            "includeSeries": str(include_series).lower(),
            "monitored": str(monitored).lower(),
        }
        return await self._get("wanted/missing", params=params)

    async def get_wanted_cutoff_unmet(
        self,
        page: int = 1,
        page_size: int = 20,
        include_series: bool = True,
    ) -> dict:
        """Get episodes that don't meet quality cutoff."""
        params = {
            "page": page,
            "pageSize": page_size,
            "includeSeries": str(include_series).lower(),
        }
        return await self._get("wanted/cutoff", params=params)

    # ==================== Commands ====================

    async def search_series_episodes(self, series_id: int) -> dict:
        """Trigger a search for all episodes of a series."""
        return await self._post(
            "command",
            json_data={"name": "SeriesSearch", "seriesId": series_id},
        )

    async def search_season(self, series_id: int, season_number: int) -> dict:
        """Trigger a search for a specific season."""
        return await self._post(
            "command",
            json_data={
                "name": "SeasonSearch",
                "seriesId": series_id,
                "seasonNumber": season_number,
            },
        )

    async def search_episodes(self, episode_ids: list[int]) -> dict:
        """Trigger a search for specific episodes."""
        return await self._post(
            "command",
            json_data={"name": "EpisodeSearch", "episodeIds": episode_ids},
        )

    async def refresh_series(self, series_id: Optional[int] = None) -> dict:
        """Refresh series information. If no series_id, refreshes all."""
        data = {"name": "RefreshSeries"}
        if series_id:
            data["seriesId"] = series_id
        return await self._post("command", json_data=data)

    async def rescan_series(self, series_id: Optional[int] = None) -> dict:
        """Rescan disk for series files. If no series_id, rescans all."""
        data = {"name": "RescanSeries"}
        if series_id:
            data["seriesId"] = series_id
        return await self._post("command", json_data=data)

    async def rss_sync(self) -> dict:
        """Trigger an RSS sync."""
        return await self._post("command", json_data={"name": "RssSync"})

    async def get_command_status(self, command_id: int) -> dict:
        """Get status of a command."""
        return await self._get(f"command/{command_id}")

    # ==================== Indexers ====================

    async def get_indexers(self) -> list:
        """Get configured indexers."""
        return await self._get("indexer")

    async def test_indexers(self) -> dict:
        """Test all indexers."""
        return await self._post("command", json_data={"name": "IndexerTest"})

    # ==================== Statistics ====================

    async def get_statistics(self) -> dict:
        """Get comprehensive statistics about the Sonarr library."""
        series = await self.get_all_series()
        disk_space = await self.get_disk_space()
        queue = await self.get_queue(page_size=1)
        wanted = await self.get_wanted_missing(page_size=1)

        # Calculate statistics
        total_series = len(series)
        monitored_series = sum(1 for s in series if s.get("monitored", False))
        continuing_series = sum(1 for s in series if s.get("status") == "continuing")
        ended_series = sum(1 for s in series if s.get("status") == "ended")

        total_episodes = sum(s.get("statistics", {}).get("totalEpisodeCount", 0) for s in series)
        episode_file_count = sum(s.get("statistics", {}).get("episodeFileCount", 0) for s in series)
        missing_episodes = sum(
            s.get("statistics", {}).get("episodeCount", 0)
            - s.get("statistics", {}).get("episodeFileCount", 0)
            for s in series
        )

        total_size_bytes = sum(s.get("statistics", {}).get("sizeOnDisk", 0) for s in series)
        total_size_gb = total_size_bytes / (1024**3)

        return {
            "series": {
                "total": total_series,
                "monitored": monitored_series,
                "unmonitored": total_series - monitored_series,
                "continuing": continuing_series,
                "ended": ended_series,
            },
            "episodes": {
                "total": total_episodes,
                "downloaded": episode_file_count,
                "missing": missing_episodes,
                "percentage_complete": round(
                    (episode_file_count / total_episodes * 100) if total_episodes > 0 else 0, 2
                ),
            },
            "storage": {
                "series_size_gb": round(total_size_gb, 2),
                "disk_space": [
                    {
                        "path": d.get("path"),
                        "free_gb": round(d.get("freeSpace", 0) / (1024**3), 2),
                        "total_gb": round(d.get("totalSpace", 0) / (1024**3), 2),
                    }
                    for d in disk_space
                ],
            },
            "queue": {
                "total_items": queue.get("totalRecords", 0),
            },
            "wanted": {
                "missing_episodes": wanted.get("totalRecords", 0),
            },
        }
