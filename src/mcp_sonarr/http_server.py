"""HTTP/SSE Transport for MCP Server - Enables remote access for Claude/ChatGPT.

This module provides a proper MCP-compliant HTTP server using StreamableHTTP transport,
making it compatible with ChatGPT's native MCP support.
"""

import os
import contextlib
import logging
from typing import Optional
from datetime import datetime, timedelta

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from .auth import (
    oauth_authorize,
    oauth_token,
    oauth_metadata,
    OAuthMiddleware,
    oauth_config,
)

import uvicorn
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .sonarr_client import SonarrClient, SonarrConfig

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server info
SERVER_NAME = "mcp-sonarr"
SERVER_VERSION = "1.0.0"

# Global client (initialized on first use)
_client: Optional[SonarrClient] = None


def get_client() -> SonarrClient:
    """Get or create the Sonarr client."""
    global _client
    if _client is None:
        url = os.getenv("SONARR_URL")
        api_key = os.getenv("SONARR_API_KEY")

        if not url or not api_key:
            raise ValueError("SONARR_URL and SONARR_API_KEY environment variables are required")

        config = SonarrConfig(url=url, api_key=api_key)
        _client = SonarrClient(config)

    return _client


def get_auth_token() -> Optional[str]:
    """Get the authentication token from environment."""
    return os.getenv("MCP_AUTH_TOKEN")


# ==================== Create FastMCP Server ====================

# Create FastMCP instance with JSON response mode for stateless operation
# Disable DNS rebinding protection since we run behind a reverse proxy
# (Traefik, nginx, Zoraxy, etc.) which handles security at the proxy layer
mcp = FastMCP(
    SERVER_NAME,
    json_response=True,  # Enables stateless mode for better compatibility
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


# ==================== Tool Definitions ====================


# System Tools
@mcp.tool()
async def sonarr_system_status() -> dict:
    """Get Sonarr system status including version, OS, and runtime information."""
    client = get_client()
    return await client.get_system_status()


@mcp.tool()
async def sonarr_health_check() -> list:
    """Get health check results showing any issues with Sonarr."""
    client = get_client()
    return await client.get_health()


@mcp.tool()
async def sonarr_get_statistics() -> dict:
    """Get comprehensive statistics about your Sonarr library including series counts, episode counts, storage usage, and queue status."""
    client = get_client()
    return await client.get_statistics()


@mcp.tool()
async def sonarr_get_disk_space() -> list:
    """Get disk space information for all root folders."""
    client = get_client()
    return await client.get_disk_space()


@mcp.tool()
async def sonarr_get_root_folders() -> list:
    """Get configured root folders where series are stored."""
    client = get_client()
    return await client.get_root_folders()


@mcp.tool()
async def sonarr_get_quality_profiles() -> list:
    """Get available quality profiles for series."""
    client = get_client()
    return await client.get_quality_profiles()


@mcp.tool()
async def sonarr_get_tags() -> list:
    """Get all tags configured in Sonarr."""
    client = get_client()
    return await client.get_tags()


# Series Tools
@mcp.tool()
async def sonarr_get_all_series() -> dict:
    """Get all series in your Sonarr library. Returns an object with 'items' array containing all series and 'total' count."""
    client = get_client()
    series = await client.get_all_series()
    # Return a simplified view wrapped in a structured object
    # This ensures the response is always an object with explicit 'items' array
    items = [
        {
            "id": s.get("id"),
            "title": s.get("title"),
            "year": s.get("year"),
            "status": s.get("status"),
            "monitored": s.get("monitored"),
            "seasons": len(s.get("seasons", [])),
            "episodeCount": s.get("statistics", {}).get("episodeCount", 0),
            "episodeFileCount": s.get("statistics", {}).get("episodeFileCount", 0),
            "percentComplete": s.get("statistics", {}).get("percentOfEpisodes", 0),
            "sizeOnDisk": s.get("statistics", {}).get("sizeOnDisk", 0),
            "added": s.get("added"),
        }
        for s in series
    ]
    return {
        "items": items,
        "total": len(items),
    }


@mcp.tool()
async def sonarr_list_series(
    status: Optional[str] = None,
    monitored: Optional[bool] = None,
    title_contains: Optional[str] = None,
    sort_by: str = "title",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List series with filtering and pagination. Returns filtered results with metadata.

    Args:
        status: Filter by status: 'ended', 'continuing', 'upcoming', or 'deleted'
        monitored: Filter by monitored status (true/false)
        title_contains: Filter by title containing this text (case-insensitive)
        sort_by: Sort results by field: 'title', 'year', 'added', 'sizeOnDisk' (default: title)
        sort_order: Sort order: 'asc' or 'desc' (default: asc)
        page: Page number (1-indexed, default: 1)
        page_size: Items per page (default: 50, max: 500)
    """
    client = get_client()
    series = await client.get_all_series()

    # Build simplified series list with additional fields for filtering
    all_items = [
        {
            "id": s.get("id"),
            "title": s.get("title"),
            "year": s.get("year"),
            "status": s.get("status"),
            "monitored": s.get("monitored"),
            "seasons": len(s.get("seasons", [])),
            "episodeCount": s.get("statistics", {}).get("episodeCount", 0),
            "episodeFileCount": s.get("statistics", {}).get("episodeFileCount", 0),
            "percentComplete": s.get("statistics", {}).get("percentOfEpisodes", 0),
            "sizeOnDisk": s.get("statistics", {}).get("sizeOnDisk", 0),
            "added": s.get("added"),
        }
        for s in series
    ]

    # Apply filters
    filtered = all_items

    # Filter by status
    if status:
        filtered = [s for s in filtered if s.get("status") == status]

    # Filter by monitored
    if monitored is not None:
        filtered = [s for s in filtered if s.get("monitored") == monitored]

    # Filter by title
    if title_contains:
        title_lower = title_contains.lower()
        filtered = [s for s in filtered if title_lower in (s.get("title") or "").lower()]

    # Sort results
    reverse = sort_order == "desc"

    if sort_by == "title":
        filtered.sort(key=lambda x: (x.get("title") or "").lower(), reverse=reverse)
    elif sort_by == "year":
        filtered.sort(key=lambda x: x.get("year") or 0, reverse=reverse)
    elif sort_by == "added":
        filtered.sort(key=lambda x: x.get("added") or "", reverse=reverse)
    elif sort_by == "sizeOnDisk":
        filtered.sort(key=lambda x: x.get("sizeOnDisk") or 0, reverse=reverse)

    # Pagination
    page = max(1, page)
    page_size = min(500, max(1, page_size))
    total_filtered = len(filtered)
    total_pages = (total_filtered + page_size - 1) // page_size if total_filtered > 0 else 1

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated = filtered[start_idx:end_idx]

    return {
        "items": paginated,
        "total": total_filtered,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "filters_applied": {
            "status": status,
            "monitored": monitored,
            "title_contains": title_contains,
        },
    }


@mcp.tool()
async def sonarr_get_series(series_id: int) -> dict:
    """Get detailed information about a specific series by its ID.

    Args:
        series_id: The Sonarr series ID
    """
    client = get_client()
    return await client.get_series(series_id)


@mcp.tool()
async def sonarr_search_new_series(term: str) -> list:
    """Search for new series to add (searches TVDB/TMDB). Use this to find series before adding them.

    Args:
        term: Search term (series name or TVDB ID with 'tvdb:' prefix)
    """
    client = get_client()
    results = await client.search_series(term)
    # Return a simplified view
    return [
        {
            "tvdbId": r.get("tvdbId"),
            "title": r.get("title"),
            "year": r.get("year"),
            "overview": (
                (r.get("overview", "")[:200] + "...")
                if len(r.get("overview", "")) > 200
                else r.get("overview", "")
            ),
            "status": r.get("status"),
            "network": r.get("network"),
            "seasons": len(r.get("seasons", [])),
        }
        for r in results
    ]


@mcp.tool()
async def sonarr_add_series(
    tvdb_id: int,
    quality_profile_id: int,
    root_folder_path: str,
    monitored: bool = True,
    search_for_missing: bool = True,
) -> dict:
    """Add a new series to Sonarr. First use sonarr_search_new_series to find the TVDB ID.

    Args:
        tvdb_id: TVDB ID of the series (get this from search results)
        quality_profile_id: Quality profile ID (use sonarr_get_quality_profiles to see available)
        root_folder_path: Root folder path (use sonarr_get_root_folders to see available)
        monitored: Whether to monitor the series for new episodes (default: true)
        search_for_missing: Whether to search for missing episodes after adding (default: true)
    """
    client = get_client()
    return await client.add_series(
        tvdb_id=tvdb_id,
        title="",  # Will be fetched from lookup
        quality_profile_id=quality_profile_id,
        root_folder_path=root_folder_path,
        monitored=monitored,
        search_for_missing=search_for_missing,
    )


@mcp.tool()
async def sonarr_delete_series(series_id: int, delete_files: bool = False) -> dict:
    """Delete a series from Sonarr.

    Args:
        series_id: The Sonarr series ID to delete
        delete_files: Also delete the files on disk (default: false)
    """
    client = get_client()
    await client.delete_series(series_id=series_id, delete_files=delete_files)
    return {"success": True, "message": f"Series {series_id} deleted"}


# Episode Tools
@mcp.tool()
async def sonarr_get_episodes(series_id: int) -> list:
    """Get all episodes for a specific series.

    Args:
        series_id: The Sonarr series ID
    """
    client = get_client()
    episodes = await client.get_episodes(series_id)
    return [
        {
            "id": e.get("id"),
            "seasonNumber": e.get("seasonNumber"),
            "episodeNumber": e.get("episodeNumber"),
            "title": e.get("title"),
            "airDate": e.get("airDate"),
            "hasFile": e.get("hasFile"),
            "monitored": e.get("monitored"),
        }
        for e in episodes
    ]


@mcp.tool()
async def sonarr_get_episode_files(series_id: int) -> list:
    """Get downloaded episode files for a series.

    Args:
        series_id: The Sonarr series ID
    """
    client = get_client()
    return await client.get_episode_files(series_id)


# Calendar Tools
@mcp.tool()
async def sonarr_get_calendar(days: int = 7, include_past_days: int = 0) -> list:
    """Get upcoming episodes from the calendar.

    Args:
        days: Number of days to look ahead (default: 7)
        include_past_days: Number of past days to include (default: 0)
    """
    client = get_client()
    start_date = (datetime.now() - timedelta(days=include_past_days)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    calendar = await client.get_calendar(start_date=start_date, end_date=end_date)
    return [
        {
            "seriesTitle": e.get("series", {}).get("title"),
            "seasonNumber": e.get("seasonNumber"),
            "episodeNumber": e.get("episodeNumber"),
            "title": e.get("title"),
            "airDate": e.get("airDateUtc"),
            "hasFile": e.get("hasFile"),
        }
        for e in calendar
    ]


# Queue Tools
@mcp.tool()
async def sonarr_get_queue(page: int = 1, page_size: int = 20) -> dict:
    """Get the current download queue.

    Args:
        page: Page number (default: 1)
        page_size: Items per page (default: 20)
    """
    client = get_client()
    queue = await client.get_queue(page=page, page_size=page_size)
    return {
        "totalRecords": queue.get("totalRecords", 0),
        "records": [
            {
                "id": r.get("id"),
                "seriesTitle": r.get("series", {}).get("title"),
                "episodeTitle": r.get("episode", {}).get("title"),
                "seasonNumber": r.get("episode", {}).get("seasonNumber"),
                "episodeNumber": r.get("episode", {}).get("episodeNumber"),
                "quality": r.get("quality", {}).get("quality", {}).get("name"),
                "size": r.get("size"),
                "sizeleft": r.get("sizeleft"),
                "status": r.get("status"),
                "trackedDownloadStatus": r.get("trackedDownloadStatus"),
                "downloadClient": r.get("downloadClient"),
            }
            for r in queue.get("records", [])
        ],
    }


@mcp.tool()
async def sonarr_delete_queue_item(queue_id: int, blocklist: bool = False) -> dict:
    """Remove an item from the download queue.

    Args:
        queue_id: Queue item ID to remove
        blocklist: Add the release to blocklist (default: false)
    """
    client = get_client()
    await client.delete_queue_item(queue_id=queue_id, blocklist=blocklist)
    return {"success": True, "message": f"Queue item {queue_id} removed"}


# History Tools
@mcp.tool()
async def sonarr_get_history(page: int = 1, page_size: int = 20) -> dict:
    """Get download history.

    Args:
        page: Page number (default: 1)
        page_size: Items per page (default: 20)
    """
    client = get_client()
    history = await client.get_history(page=page, page_size=page_size)
    return {
        "totalRecords": history.get("totalRecords", 0),
        "records": [
            {
                "id": r.get("id"),
                "seriesTitle": r.get("series", {}).get("title"),
                "episodeTitle": r.get("episode", {}).get("title"),
                "seasonNumber": r.get("episode", {}).get("seasonNumber"),
                "episodeNumber": r.get("episode", {}).get("episodeNumber"),
                "date": r.get("date"),
                "eventType": r.get("eventType"),
                "quality": r.get("quality", {}).get("quality", {}).get("name"),
            }
            for r in history.get("records", [])
        ],
    }


# Wanted Tools
@mcp.tool()
async def sonarr_get_missing_episodes(page: int = 1, page_size: int = 20) -> dict:
    """Get wanted/missing episodes.

    Args:
        page: Page number (default: 1)
        page_size: Items per page (default: 20)
    """
    client = get_client()
    missing = await client.get_wanted_missing(page=page, page_size=page_size)
    return {
        "totalRecords": missing.get("totalRecords", 0),
        "records": [
            {
                "id": r.get("id"),
                "seriesTitle": r.get("series", {}).get("title"),
                "seasonNumber": r.get("seasonNumber"),
                "episodeNumber": r.get("episodeNumber"),
                "title": r.get("title"),
                "airDate": r.get("airDate"),
            }
            for r in missing.get("records", [])
        ],
    }


# Command Tools
@mcp.tool()
async def sonarr_search_series(series_id: int) -> dict:
    """Trigger a search for all missing episodes of a series.

    Args:
        series_id: The Sonarr series ID to search
    """
    client = get_client()
    result = await client.search_series_episodes(series_id)
    return {"success": True, "commandId": result.get("id"), "message": "Search initiated"}


@mcp.tool()
async def sonarr_search_season(series_id: int, season_number: int) -> dict:
    """Trigger a search for all episodes of a specific season.

    Args:
        series_id: The Sonarr series ID
        season_number: Season number to search
    """
    client = get_client()
    result = await client.search_season(series_id=series_id, season_number=season_number)
    return {"success": True, "commandId": result.get("id"), "message": "Search initiated"}


@mcp.tool()
async def sonarr_refresh_series(series_id: Optional[int] = None) -> dict:
    """Refresh series information from TVDB/TMDB.

    Args:
        series_id: Series ID to refresh (omit to refresh all)
    """
    client = get_client()
    result = await client.refresh_series(series_id)
    return {"success": True, "commandId": result.get("id"), "message": "Refresh initiated"}


@mcp.tool()
async def sonarr_rescan_series(series_id: Optional[int] = None) -> dict:
    """Rescan disk for series files.

    Args:
        series_id: Series ID to rescan (omit to rescan all)
    """
    client = get_client()
    result = await client.rescan_series(series_id)
    return {"success": True, "commandId": result.get("id"), "message": "Rescan initiated"}


@mcp.tool()
async def sonarr_rss_sync() -> dict:
    """Trigger an RSS sync to check indexers for new releases."""
    client = get_client()
    result = await client.rss_sync()
    return {"success": True, "commandId": result.get("id"), "message": "RSS sync initiated"}


# ==================== Custom Routes ====================


async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    try:
        client = get_client()
        status = await client.get_system_status()
        return JSONResponse(
            {
                "status": "healthy",
                "server": SERVER_NAME,
                "version": SERVER_VERSION,
                "sonarr_version": status.get("version"),
            }
        )
    except Exception as e:
        return JSONResponse(
            {"status": "unhealthy", "error": str(e)},
            status_code=503,
        )


async def server_info(request: Request) -> JSONResponse:
    """Get server information."""
    return JSONResponse(
        {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
        }
    )


# ==================== Application Setup ====================

# Configure the MCP path to be at /mcp
mcp.settings.streamable_http_path = "/"


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    """Manage application lifespan - initialize and cleanup MCP session manager."""
    async with mcp.session_manager.run():
        logger.info(f"MCP Sonarr server started - {SERVER_NAME} v{SERVER_VERSION}")
        yield
        logger.info("MCP Sonarr server stopping")


# Create custom routes
custom_routes = [
    Route("/health", endpoint=health, methods=["GET"]),
    Route("/info", endpoint=server_info, methods=["GET"]),
    # OAuth 2.0 endpoints
    Route("/oauth/authorize", endpoint=oauth_authorize, methods=["GET", "POST"]),
    Route("/oauth/token", endpoint=oauth_token, methods=["POST"]),
    Route("/.well-known/oauth-authorization-server", endpoint=oauth_metadata, methods=["GET"]),
]

# Create middleware for CORS, auth, and proxy headers
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    ),
    Middleware(OAuthMiddleware),
]

# Create the main application
app = Starlette(
    routes=[
        *custom_routes,
        # Mount the MCP streamable HTTP app at /mcp
        Mount("/mcp", app=mcp.streamable_http_app()),
    ],
    middleware=middleware,
    lifespan=lifespan,
)


def main():
    """Run the HTTP server."""
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8080"))

    logger.info(f"Starting MCP Sonarr HTTP server on {host}:{port}")
    logger.info(f"MCP endpoint available at: http://{host}:{port}/mcp")
    logger.info(f"Health check available at: http://{host}:{port}/health")

    # Log authentication status
    if oauth_config.oauth_enabled:
        logger.info("OAuth 2.0 authentication enabled")
        logger.info(f"Authorization endpoint: http://{host}:{port}/oauth/authorize")
        logger.info(f"Token endpoint: http://{host}:{port}/oauth/token")
    elif oauth_config.simple_auth_token:
        logger.info("Simple Bearer token authentication enabled")
    else:
        logger.warning("No authentication configured - server is open to all requests")

    # Run with proxy headers support for reverse proxy deployments (Traefik, nginx, etc.)
    # This fixes 421 Misdirected Request errors when behind a reverse proxy
    uvicorn.run(
        app,
        host=host,
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
