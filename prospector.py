"""
PMOVES-BoTZ Batch Prospector

Orchestrates search -> inspect -> rank -> draft pipeline.
Agent Zero supplies search results; prospector processes and ranks them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from inspector import inspect_channel, load_config
from commenter import draft_comments


DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
DEFAULT_LOG_DIR = Path(__file__).parent / "logs"


def _ensure_log_dir(log_dir: Path | None = None) -> Path:
    d = log_dir or DEFAULT_LOG_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _log_prospect(results: list[dict], query: str, log_dir: Path | None = None):
    d = _ensure_log_dir(log_dir)
    log_file = d / "prospect_log.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "channels_found": len(results),
        "results": results,
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _deduplicate_channels(
    search_results: list[dict],
) -> dict[str, dict]:
    """Deduplicate search results by channel ID/name.

    Args:
        search_results: List of dicts from youtube_search, e.g.:
            [{"id": "abc", "title": "...", "channel": "Cole Medin", "channel_id": "UC..."}, ...]

    Returns:
        Dict mapping channel_id -> {channel_info, videos: [...]}
    """
    channels: dict[str, dict] = {}
    for r in search_results:
        ch_id = r.get("channel_id", "")
        ch_name = r.get("channel", r.get("channel_title", "Unknown"))
        # Use channel name as fallback key if no ID
        key = ch_id or ch_name

        if key not in channels:
            channels[key] = {
                "channel_info": {
                    "id": ch_id,
                    "name": ch_name,
                    "url": r.get("channel_url", ""),
                },
                "videos": [],
            }
        channels[key]["videos"].append({
            "id": r.get("id", ""),
            "title": r.get("title", ""),
            "description": r.get("description", ""),
            "published_at": r.get("published_at", ""),
        })

    return channels


def prospect(
    search_results: list[dict],
    query: str,
    channel_details: dict[str, dict] | None = None,
    transcripts: dict[str, list[str]] | None = None,
 limit: int | None = None,
 config_path: str | Path | None = None,
) -> dict:
    """
    Run full prospecting pipeline on search results.

    Args:
        search_results: List of dicts from youtube_search tool.
        query: The search query used.
        channel_details: Optional dict of channel_id -> channel_data
            (from youtube_read channel) for subscriber counts etc.
        transcripts: Optional dict of channel_id -> [transcript strings].
        limit: Max channels to process (default from config).
        config_path: Optional path to config.yaml.

    Returns:
        Dict with ranked prospects and metadata.
    """
    config = load_config(config_path)
    limit = limit or config.get("prospecting", {}).get("default_limit", 10)
    log_dir = Path(__file__).parent / config.get("logging", {}).get("dir", "logs")
    min_score = config["scoring"]["threshold"]["prospect"]

    channel_details = channel_details or {}
    transcripts = transcripts or {}

    # Deduplicate by channel
    channels = _deduplicate_channels(search_results)

    # Enrich with channel details if available
    for key, ch_data in channels.items():
        ch_id = ch_data["channel_info"]["id"]
        if ch_id in channel_details:
            detail = channel_details[ch_id]
            ch_data["channel_info"].update({
                "description": detail.get("description", ""),
                "subscriber_count": detail.get("subscriber_count", 0),
                "url": detail.get("url", ch_data["channel_info"].get("url", "")),
            })

    # Inspect each channel (up to limit)
    inspected = []
    channel_keys = list(channels.keys())[:limit]

    for key in channel_keys:
        ch = channels[key]
        ch_info = ch["channel_info"]
        vids = ch["videos"]
        ch_transcripts = transcripts.get(key, transcripts.get(ch_info["id"], []))

        result = inspect_channel(
            channel_data=ch_info,
            video_data=vids,
            transcripts=ch_transcripts,
            config_path=config_path,
        )
        inspected.append(result)

    # Sort by fit score descending
    inspected.sort(key=lambda x: x["fit"]["total_score"], reverse=True)

    # Filter below threshold
    qualified = [r for r in inspected if r["fit"]["total_score"] >= min_score]

    # Draft comments for top qualified prospects
    draft_results = []
    for r in qualified:
        if r["recommendations"]["should_draft"] and r["channel"]["videos_analyzed"] > 0:
            # Use first video for comment drafting
            first_vid = channels.get(
                r["channel"]["id"], {}
            ).get("videos", [{}])[0] if r["channel"]["id"] in channels else {}
            if not first_vid:
                # Fallback: use channel info to construct video data
                first_vid = {
                    "id": "unknown",
                    "title": r["channel"]["name"] + " (recent video)",
                    "description": "",
                    "channel_name": r["channel"]["name"],
                }
            first_vid["channel_name"] = r["channel"]["name"]
            drafts = draft_comments(
                video_data=first_vid,
                fit_result=r,
                config_path=config_path,
            )
            draft_results.append(drafts)

    # Build final result
    result = {
        "query": query,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_channels_found": len(channels),
        "channels_inspected": len(inspected),
        "channels_qualified": len(qualified),
        "min_score_threshold": min_score,
        "ranked_prospects": [
            {
                "rank": i + 1,
                "channel_name": r["channel"]["name"],
                "channel_id": r["channel"]["id"],
                "score": r["fit"]["total_score"],
                "priority": r["recommendations"]["priority"],
                "topic_score": r["fit"]["topic_score"],
                "quality_score": r["fit"]["quality_score"],
                "angle_score": r["fit"]["angle_score"],
                "top_signals": [
                    h["label"] for h in r["fit"]["topic_hits"][:3]
                ] + [
                    h["label"] for h in r["fit"]["angle_hits"][:2]
                ],
                "comment_angles": r["fit"]["comment_angles"][:2],
            }
            for i, r in enumerate(qualified)
        ],
        "draft_comments": draft_results,
    }

    _log_prospect(result["ranked_prospects"], query, log_dir)

    return result


def format_prospect_output(result: dict) -> str:
    """Format prospect results for terminal output."""
    lines = [
        f"# PMOVES Prospect Report: {result['query']}",
        f"Generated: {result['timestamp']}",
        "",
        f"## Summary",
        f"- Channels found: {result['total_channels_found']}",
        f"- Channels inspected: {result['channels_inspected']}",
        f"- Qualified (score >= {result['min_score_threshold']}): {result['channels_qualified']}",
        "",
    ]

    if not result["ranked_prospects"]:
        lines.append("No channels met the minimum score threshold.")
        return "\n".join(lines)

    lines.append("## Ranked Prospects")
    for p in result["ranked_prospects"]:
        lines.append("")
        lines.append(
            f"### #{p['rank']} {p['channel_name']} -- Score: {p['score']}/100 [{p['priority'].upper()}]"
        )
        lines.append(f"  Topic: {p['topic_score']}/60 | Quality: {p['quality_score']}/40 | Angle: {p['angle_score']}/60")
        if p["top_signals"]:
            lines.append(f"  Signals: {', '.join(p['top_signals'])}")
        if p["comment_angles"]:
            lines.append(f"  Comment angles:")
            for angle in p["comment_angles"]:
                lines.append(f"    - {angle}")

    if result["draft_comments"]:
        lines.append("")
        lines.append("## Draft Comments (Top Prospects)")
        for dc in result["draft_comments"]:
            lines.append("")
            lines.append(f"### {dc['channel_name']} -- {dc['video_title']}")
            for i, d in enumerate(dc["drafts"], 1):
                lines.append(f"**Draft {i} ({d['angle']}):**")
                lines.append(d["text"])
                lines.append("")

    return "\n".join(lines)
