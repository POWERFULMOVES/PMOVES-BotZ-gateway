"""
PMOVES-BoTZ — YouTube Prospecting & Engagement CLI

Designed to be called BY Agent Zero with data from youtube_* tools.
CLI mode demonstrates usage; real power is in the Python API.

Usage:
    python botz.py inspect --help
    python botz.py draft --help
    python botz.py prospect --help
    python botz.py demo
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from signals import score_channel, fit_score_to_dict, format_fit_report
from inspector import inspect_channel, format_inspect_output
from commenter import draft_comments, log_post_result, format_drafts_output
from prospector import prospect, format_prospect_output


def cmd_inspect(args):
    """Inspect a channel using provided JSON data."""
    if args.json:
        with open(args.json) as f:
            data = json.load(f)
        channel_data = data.get("channel", {})
        video_data = data.get("videos", [])
        transcripts = data.get("transcripts", [])
    else:
        print("ERROR: inspect requires --json with channel data from Agent Zero youtube tools.")
        print("")
        print("Expected JSON format:")
        print(json.dumps({
            "channel": {
                "id": "UC...",
                "name": "Channel Name",
                "description": "Channel description...",
                "subscriber_count": 50000,
                "url": "https://youtube.com/@handle",
            },
            "videos": [
                {
                    "id": "abc123",
                    "title": "Video about AI coding harnesses",
                    "description": "Building autonomous coding pipelines...",
                    "published_at": "2026-04-20T12:00:00Z",
                },
            ],
            "transcripts": ["optional transcript text..."],
        }, indent=2))
        return 1

    result = inspect_channel(channel_data, video_data, transcripts)
    print(format_inspect_output(result))
    return 0


def cmd_draft(args):
    """Draft comments for a video using provided JSON data."""
    if args.json:
        with open(args.json) as f:
            data = json.load(f)
        video_data = data.get("video", {})
        fit_result = data.get("fit_result")
    else:
        print("ERROR: draft requires --json with video data from Agent Zero youtube tools.")
        print("")
        print("Expected JSON format:")
        print(json.dumps({
            "video": {
                "id": "BGpYeE1dKI8",
                "title": "Pushing My Dark Factory Further with Kimi K2.6",
                "description": "A codebase that writes its own code, live...",
                "channel_name": "Cole Medin",
                "transcript": "optional transcript...",
            },
            "fit_result": "optional result from inspect_channel",
        }, indent=2))
        return 1

    result = draft_comments(video_data, fit_result)
    print(format_drafts_output(result))
    return 0


def cmd_prospect(args):
    """Run batch prospecting using provided JSON data."""
    if args.json:
        with open(args.json) as f:
            data = json.load(f)
        search_results = data.get("search_results", [])
        query = data.get("query", "unknown")
        channel_details = data.get("channel_details")
        transcripts = data.get("transcripts")
    else:
        print("ERROR: prospect requires --json with search results from Agent Zero youtube_search.")
        print("")
        print("Expected JSON format:")
        print(json.dumps({
            "query": "AI multi-agent framework",
            "search_results": [
                {
                    "id": "abc123",
                    "title": "Building Multi-Agent AI Systems",
                    "channel": "Tech Creator",
                    "channel_id": "UC...",
                    "description": "In this video we build...",
                    "published_at": "2026-04-15T10:00:00Z",
                },
            ],
            "channel_details": {
                "UC...": {"subscriber_count": 10000, "description": "..."},
            },
            "transcripts": {
                "UC...": ["transcript text..."],
            },
        }, indent=2))
        return 1

    result = prospect(
        search_results=search_results,
        query=query,
        channel_details=channel_details,
        transcripts=transcripts,
        limit=args.limit,
    )
    print(format_prospect_output(result))
    return 0


def cmd_demo(args):
    """Run a demo with sample data to show how BoTZ works."""
    print("=" * 60)
    print("PMOVES-BoTZ Demo Mode")
    print("=" * 60)
    print()

    # Demo channel inspection
    sample_channel = {
        "id": "UCfake123",
        "name": "Cole Medin (Demo)",
        "description": "Building AI coding harnesses, dark factories, and autonomous pipelines with Claude Code and Archon.",
        "subscriber_count": 85000,
        "url": "https://youtube.com/@coleam00",
    }
    sample_videos = [
        {
            "id": "v1",
            "title": "Full Archon Guide - Build AI Coding Harnesses That Actually Ship (LIVE)",
            "description": "Building a coding harness with dark factory pattern, context engineering, and multi-agent delegation.",
            "published_at": "2026-04-20T12:00:00Z",
        },
        {
            "id": "v2",
            "title": "Self-Evolving Claude Code Memory with Karpathy Knowledge Bases",
            "description": "Long-term memory for AI coding using RAG and knowledge bases.",
            "published_at": "2026-04-15T10:00:00Z",
        },
        {
            "id": "v3",
            "title": "Pushing My Dark Factory Further with Kimi K2.6",
            "description": "A codebase that writes its own code, live. Autonomous coding pipeline.",
            "published_at": "2026-04-24T18:00:00Z",
        },
    ]
    sample_transcripts = [
        "The dark factory concept is about building a fully autonomous coding pipeline where AI codes, tests, reviews, and ships with zero human intervention. Context engineering is the idea of structuring the context rather than just writing prompts. The harness pattern wraps around Claude Code with skills, knowledge base, and task management. MCP server integration allows any AI coding assistant to connect. Supabase for persistence, multi-agent delegation for parallel work.",
    ]

    print("## 1. Channel Inspection")
    print("-" * 40)
    result = inspect_channel(sample_channel, sample_videos, sample_transcripts)
    print(format_inspect_output(result))
    print()

    # Demo comment drafting
    print("## 2. Comment Drafting")
    print("-" * 40)
    video_data = {
        "id": "v3",
        "title": "Pushing My Dark Factory Further with Kimi K2.6: A Codebase That Writes Its Own Code, Live",
        "description": "A codebase that writes its own code, live. Dark factory autonomous coding pipeline with Kimi K2.6.",
        "channel_name": "Cole Medin (Demo)",
    }
    drafts = draft_comments(video_data, result)
    print(format_drafts_output(drafts))
    print()

    # Demo scoring engine directly
    print("## 3. Direct Scoring API")
    print("-" * 40)
    fit = score_channel(
        video_titles=["multi-agent orchestration with NATS message bus"],
        video_descriptions=["building distributed agent fleets"],
        transcripts=["coordination ceiling single agent bottleneck fleet of agents"],
        subscriber_count=5000,
        recent_video_days=7,
        has_technical_content=True,
        builds_in_public=True,
    )
    print(format_fit_report(fit, "Generic Multi-Agent Channel"))

    print()
    print("=" * 60)
    print("Demo complete. In production, Agent Zero calls these functions")
    print("directly with data from youtube_* tools.")
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="botz",
        description="PMOVES-BoTZ -- YouTube Prospecting & Engagement for PMOVES.AI",
        epilog="Designed to be called BY Agent Zero. CLI mode demonstrates usage.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect a channel for PMOVES fit score")
    p_inspect.add_argument("--json", help="Path to JSON file with channel+video data")
    p_inspect.set_defaults(func=cmd_inspect)

    # draft
    p_draft = subparsers.add_parser("draft", help="Draft contextual comments for a video")
    p_draft.add_argument("--json", help="Path to JSON file with video data")
    p_draft.set_defaults(func=cmd_draft)

    # prospect
    p_prospect = subparsers.add_parser("prospect", help="Batch prospect channels from search results")
    p_prospect.add_argument("--json", help="Path to JSON file with search results")
    p_prospect.add_argument("--limit", type=int, default=None, help="Max channels to inspect")
    p_prospect.set_defaults(func=cmd_prospect)

    # demo
    p_demo = subparsers.add_parser("demo", help="Run demo with sample data")
    p_demo.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
