"""
PMOVES-BoTZ Channel Inspector

Inspects YouTube channels for PMOVES fit scoring.
Designed to be called BY Agent Zero with data from youtube_* tools.
Does NOT call YouTube APIs directly.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from signals import FitScore, fit_score_to_dict, format_fit_report, score_channel


DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"
DEFAULT_LOG_DIR = Path(__file__).parent / "logs"


def load_config(config_path: str | Path | None = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with open(path) as f:
        return yaml.safe_load(f)


def _ensure_log_dir(log_dir: Path | None = None) -> Path:
    d = log_dir or DEFAULT_LOG_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d

def _log_inspect(channel_id: str, channel_name: str, fit_dict: dict, log_dir: Path | None = None):
    d = _ensure_log_dir(log_dir)
    log_file = d / "inspect_log.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "channel_id": channel_id,
        "channel_name": channel_name,
        **fit_dict,
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _estimate_recent_video_days(published_dates: list[str] | None) -> Optional[int]:
    """Estimate days since most recent video from ISO date strings."""
    if not published_dates:
        return None
    now = datetime.now(timezone.utc)
    min_days = None
    for ds in published_dates:
        try:
            dt = datetime.fromisoformat(ds.replace("Z", "+00:00"))
            days = (now - dt).days
            if min_days is None or days < min_days:
                min_days = days
        except (ValueError, AttributeError):
            continue
    return min_days


def _detect_technical_depth(titles: list[str], descriptions: list[str]) -> bool:
    """Heuristic: channel shows technical depth if titles contain code/tech terms."""
    combined = " ".join(titles + descriptions).lower()
    tech_indicators = [
        "tutorial", "guide", "build", "implement", "code", "api",
        "architecture", "framework", "debug", "deploy", "setup",
        "configure", "install", "benchmark", "optimiz",
    ]
    return any(ind in combined for ind in tech_indicators)


def _detect_builds_in_public(titles: list[str], descriptions: list[str]) -> bool:
    """Heuristic: creator builds in public if they show live coding/workflows."""
    combined = " ".join(titles + descriptions).lower()
    bip_indicators = [
        "live", "in real time", "from scratch", "step by step",
        "building", "let me build", "watch me", "coding live",
        "stream", "building in public", "walkthrough",
    ]
    return any(ind in combined for ind in bip_indicators)


def inspect_channel(
    channel_data: dict,
    video_data: list[dict] | None = None,
    transcripts: list[str] | None = None,
    config_path: str | Path | None = None,
) -> dict:
    """
    Inspect a channel and compute PMOVES fit score.

    Args:
        channel_data: Dict from youtube_read channel info, e.g.:
            {
                "id": "UC...",
                "name": "Cole Medin",
                "description": "...",
                "subscriber_count": 50000,
                "url": "https://...",
            }
        video_data: List of dicts from youtube_read my_videos or search, e.g.:
            [
                {"id": "abc", "title": "...", "description": "...", "published_at": "2026-04-20T..."},
            ]
        transcripts: List of transcript strings for key videos.
        config_path: Optional path to config.yaml.

    Returns:
        Dict with fit score breakdown and metadata.
    """
    config = load_config(config_path)
    video_data = video_data or []
    transcripts = transcripts or []

    channel_id = channel_data.get("id", "unknown")
    channel_name = channel_data.get("name", channel_data.get("title", "Unknown"))
    channel_desc = channel_data.get("description", "")
    sub_count = channel_data.get("subscriber_count", 0)
    # Handle string subscriber counts
    if isinstance(sub_count, str):
        sub_count = int(sub_count.replace(",", "").replace(" ", ""))

    titles = [v.get("title", "") for v in video_data]
    descriptions = [v.get("description", "") for v in video_data]
    pub_dates = [v.get("published_at", "") for v in video_data]

    recent_days = _estimate_recent_video_days(pub_dates)
    has_tech = _detect_technical_depth(titles, descriptions)
    has_bip = _detect_builds_in_public(titles, descriptions)

    fit = score_channel(
        video_titles=titles,
        video_descriptions=descriptions,
        transcripts=transcripts,
        channel_description=channel_desc,
        subscriber_count=sub_count,
        recent_video_days=recent_days,
        has_technical_content=has_tech,
        builds_in_public=has_bip,
    )

    fit_dict = fit_score_to_dict(fit)
    log_dir = Path(__file__).parent / config.get("logging", {}).get("dir", "logs")
    _log_inspect(channel_id, channel_name, fit_dict, log_dir)

    return {
        "channel": {
            "id": channel_id,
            "name": channel_name,
            "url": channel_data.get("url", ""),
            "subscriber_count": sub_count,
            "recent_video_days": recent_days,
            "videos_analyzed": len(video_data),
            "transcripts_analyzed": len(transcripts),
        },
        "fit": fit_dict,
        "report": format_fit_report(fit, channel_name),
        "recommendations": {
            "should_engage": fit.total >= config["scoring"]["threshold"]["engage"],
            "should_draft": fit.total >= config["scoring"]["threshold"]["draft"],
            "priority": "high" if fit.total >= 60 else "medium" if fit.total >= 40 else "low",
        },
    }


def format_inspect_output(result: dict) -> str:
    """Format inspect result for terminal output."""
    ch = result["channel"]
    fit = result["fit"]
    rec = result["recommendations"]

    lines = [
        result["report"],
        "## Channel Metadata",
        f"- Subscribers: {ch['subscriber_count']:,}",
        f"- Recent video: {ch['recent_video_days']} days ago" if ch['recent_video_days'] is not None else "- Recent video: unknown",
        f"- Videos analyzed: {ch['videos_analyzed']}",
        f"- Transcripts analyzed: {ch['transcripts_analyzed']}",
        "",
        "## Recommendation",
        f"- Priority: {rec['priority'].upper()}",
        f"- Engage: {'YES' if rec['should_engage'] else 'NO'}",
        f"- Draft comments: {'YES' if rec['should_draft'] else 'NO'}",
    ]
    return "\n".join(lines)
