"""MCP Server for Sonarr - Main server implementation."""

import os
import json
import asyncio
from typing import Optional
from datetime import datetime, timedelta

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from dotenv import load_dotenv

from .sonarr_client import SonarrClient, SonarrConfig

# Load environment variables
load_dotenv()

# Initialize server
server = Server("mcp-sonarr")

# Global client (initialized on first use)
_client: Optional[SonarrClient] = None


def get_client() -> SonarrClient:
    """Get or create the Sonarr client."""
    global _client
    if _client is None:
        url = os.getenv("SONARR_URL")
        api_key = os.getenv("SONARR_API_KEY")

        if not url or not api_key:
            raise ValueError(
                "SONARR_URL and SONARR_API_KEY environment variables are required"
            )

        config = SonarrConfig(url=url, api_key=api_key)
        _client = SonarrClient(config)

    return _client


def format_response(data: any) -> str:
    """Format response data as JSON string."""
    return json.dumps(data, indent=2, default=str)


# ==================== Tool Definitions ====================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Sonarr tools."""
    return [
        # System Tools
        Tool(
            name="sonarr_system_status",
            description="Get Sonarr system status including version, OS, and runtime information",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="sonarr_health_check",
            description="Get health check results showing any issues with Sonarr",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="sonarr_get_statistics",
            description="Get comprehensive statistics about your Sonarr library including series counts, episode counts, storage usage, and queue status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="sonarr_get_disk_space",
            description="Get disk space information for all root folders",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="sonarr_get_root_folders",
            description="Get configured root folders where series are stored",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="sonarr_get_quality_profiles",
            description="Get available quality profiles for series",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="sonarr_get_tags",
            description="Get all tags configured in Sonarr",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),

        # Series Tools
        Tool(
            name="sonarr_get_all_series",
            description="Get all series in your Sonarr library",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="sonarr_get_series",
            description="Get detailed information about a specific series by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "integer",
                        "description": "The Sonarr series ID",
                    },
                },
                "required": ["series_id"],
            },
        ),
        Tool(
            name="sonarr_search_new_series",
            description="Search for new series to add (searches TVDB/TMDB). Use this to find series before adding them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "Search term (series name or TVDB ID with 'tvdb:' prefix)",
                    },
                },
                "required": ["term"],
            },
        ),
        Tool(
            name="sonarr_add_series",
            description="Add a new series to Sonarr. First use sonarr_search_new_series to find the TVDB ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tvdb_id": {
                        "type": "integer",
                        "description": "TVDB ID of the series (get this from search results)",
                    },
                    "quality_profile_id": {
                        "type": "integer",
                        "description": "Quality profile ID (use sonarr_get_quality_profiles to see available)",
                    },
                    "root_folder_path": {
                        "type": "string",
                        "description": "Root folder path (use sonarr_get_root_folders to see available)",
                    },
                    "monitored": {
                        "type": "boolean",
                        "description": "Whether to monitor the series for new episodes (default: true)",
                        "default": True,
                    },
                    "search_for_missing": {
                        "type": "boolean",
                        "description": "Whether to search for missing episodes after adding (default: true)",
                        "default": True,
                    },
                },
                "required": ["tvdb_id", "quality_profile_id", "root_folder_path"],
            },
        ),
        Tool(
            name="sonarr_delete_series",
            description="Delete a series from Sonarr",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "integer",
                        "description": "The Sonarr series ID to delete",
                    },
                    "delete_files": {
                        "type": "boolean",
                        "description": "Also delete the files on disk (default: false)",
                        "default": False,
                    },
                },
                "required": ["series_id"],
            },
        ),

        # Episode Tools
        Tool(
            name="sonarr_get_episodes",
            description="Get all episodes for a specific series",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "integer",
                        "description": "The Sonarr series ID",
                    },
                },
                "required": ["series_id"],
            },
        ),
        Tool(
            name="sonarr_get_episode_files",
            description="Get downloaded episode files for a series",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "integer",
                        "description": "The Sonarr series ID",
                    },
                },
                "required": ["series_id"],
            },
        ),

        # Calendar Tools
        Tool(
            name="sonarr_get_calendar",
            description="Get upcoming episodes from the calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 7)",
                        "default": 7,
                    },
                    "include_past_days": {
                        "type": "integer",
                        "description": "Number of past days to include (default: 0)",
                        "default": 0,
                    },
                },
                "required": [],
            },
        ),

        # Queue Tools
        Tool(
            name="sonarr_get_queue",
            description="Get the current download queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {
                        "type": "integer",
                        "description": "Page number (default: 1)",
                        "default": 1,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Items per page (default: 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="sonarr_delete_queue_item",
            description="Remove an item from the download queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "queue_id": {
                        "type": "integer",
                        "description": "Queue item ID to remove",
                    },
                    "blocklist": {
                        "type": "boolean",
                        "description": "Add the release to blocklist (default: false)",
                        "default": False,
                    },
                },
                "required": ["queue_id"],
            },
        ),

        # History Tools
        Tool(
            name="sonarr_get_history",
            description="Get download history",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {
                        "type": "integer",
                        "description": "Page number (default: 1)",
                        "default": 1,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Items per page (default: 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
        ),

        # Wanted Tools
        Tool(
            name="sonarr_get_missing_episodes",
            description="Get wanted/missing episodes",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {
                        "type": "integer",
                        "description": "Page number (default: 1)",
                        "default": 1,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Items per page (default: 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
        ),

        # Command Tools
        Tool(
            name="sonarr_search_series",
            description="Trigger a search for all missing episodes of a series",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "integer",
                        "description": "The Sonarr series ID to search",
                    },
                },
                "required": ["series_id"],
            },
        ),
        Tool(
            name="sonarr_search_season",
            description="Trigger a search for all episodes of a specific season",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "integer",
                        "description": "The Sonarr series ID",
                    },
                    "season_number": {
                        "type": "integer",
                        "description": "Season number to search",
                    },
                },
                "required": ["series_id", "season_number"],
            },
        ),
        Tool(
            name="sonarr_refresh_series",
            description="Refresh series information from TVDB/TMDB",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "integer",
                        "description": "Series ID to refresh (omit to refresh all)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="sonarr_rescan_series",
            description="Rescan disk for series files",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "integer",
                        "description": "Series ID to rescan (omit to rescan all)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="sonarr_rss_sync",
            description="Trigger an RSS sync to check indexers for new releases",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


# ==================== Tool Handlers ====================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        client = get_client()
        result = await _execute_tool(client, name, arguments)
        return [TextContent(type="text", text=format_response(result))]
    except Exception as e:
        error_response = {"error": str(e), "tool": name, "arguments": arguments}
        return [TextContent(type="text", text=format_response(error_response))]


async def _execute_tool(client: SonarrClient, name: str, arguments: dict) -> any:
    """Execute a tool and return the result."""

    # System Tools
    if name == "sonarr_system_status":
        return await client.get_system_status()

    elif name == "sonarr_health_check":
        return await client.get_health()

    elif name == "sonarr_get_statistics":
        return await client.get_statistics()

    elif name == "sonarr_get_disk_space":
        return await client.get_disk_space()

    elif name == "sonarr_get_root_folders":
        return await client.get_root_folders()

    elif name == "sonarr_get_quality_profiles":
        return await client.get_quality_profiles()

    elif name == "sonarr_get_tags":
        return await client.get_tags()

    # Series Tools
    elif name == "sonarr_get_all_series":
        series = await client.get_all_series()
        # Return a simplified view for readability
        return [
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
            }
            for s in series
        ]

    elif name == "sonarr_get_series":
        return await client.get_series(arguments["series_id"])

    elif name == "sonarr_search_new_series":
        results = await client.search_series(arguments["term"])
        # Return a simplified view
        return [
            {
                "tvdbId": r.get("tvdbId"),
                "title": r.get("title"),
                "year": r.get("year"),
                "overview": r.get("overview", "")[:200] + "..." if len(r.get("overview", "")) > 200 else r.get("overview", ""),
                "status": r.get("status"),
                "network": r.get("network"),
                "seasons": len(r.get("seasons", [])),
            }
            for r in results
        ]

    elif name == "sonarr_add_series":
        return await client.add_series(
            tvdb_id=arguments["tvdb_id"],
            title="",  # Will be fetched from lookup
            quality_profile_id=arguments["quality_profile_id"],
            root_folder_path=arguments["root_folder_path"],
            monitored=arguments.get("monitored", True),
            search_for_missing=arguments.get("search_for_missing", True),
        )

    elif name == "sonarr_delete_series":
        await client.delete_series(
            series_id=arguments["series_id"],
            delete_files=arguments.get("delete_files", False),
        )
        return {"success": True, "message": f"Series {arguments['series_id']} deleted"}

    # Episode Tools
    elif name == "sonarr_get_episodes":
        episodes = await client.get_episodes(arguments["series_id"])
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

    elif name == "sonarr_get_episode_files":
        return await client.get_episode_files(arguments["series_id"])

    # Calendar Tools
    elif name == "sonarr_get_calendar":
        days = arguments.get("days", 7)
        past_days = arguments.get("include_past_days", 0)

        start_date = (datetime.now() - timedelta(days=past_days)).strftime("%Y-%m-%d")
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
    elif name == "sonarr_get_queue":
        queue = await client.get_queue(
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 20),
        )
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

    elif name == "sonarr_delete_queue_item":
        await client.delete_queue_item(
            queue_id=arguments["queue_id"],
            blocklist=arguments.get("blocklist", False),
        )
        return {"success": True, "message": f"Queue item {arguments['queue_id']} removed"}

    # History Tools
    elif name == "sonarr_get_history":
        history = await client.get_history(
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 20),
        )
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
    elif name == "sonarr_get_missing_episodes":
        missing = await client.get_wanted_missing(
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 20),
        )
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
    elif name == "sonarr_search_series":
        result = await client.search_series_episodes(arguments["series_id"])
        return {"success": True, "commandId": result.get("id"), "message": "Search initiated"}

    elif name == "sonarr_search_season":
        result = await client.search_season(
            series_id=arguments["series_id"],
            season_number=arguments["season_number"],
        )
        return {"success": True, "commandId": result.get("id"), "message": "Search initiated"}

    elif name == "sonarr_refresh_series":
        result = await client.refresh_series(arguments.get("series_id"))
        return {"success": True, "commandId": result.get("id"), "message": "Refresh initiated"}

    elif name == "sonarr_rescan_series":
        result = await client.rescan_series(arguments.get("series_id"))
        return {"success": True, "commandId": result.get("id"), "message": "Rescan initiated"}

    elif name == "sonarr_rss_sync":
        result = await client.rss_sync()
        return {"success": True, "commandId": result.get("id"), "message": "RSS sync initiated"}

    else:
        raise ValueError(f"Unknown tool: {name}")


def main():
    """Main entry point for the MCP server."""
    import sys

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
