"""
PMOVES-BoTZ Test Suite
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from signals import (
    score_channel, score_topics, score_quality, score_angles,
    fit_score_to_dict, format_fit_report, TOPIC_SIGNALS, ANGLE_SIGNALS,
)
from inspector import inspect_channel, _detect_technical_depth, _detect_builds_in_public
from commenter import draft_comments, _extract_video_specifics, log_post_result
from prospector import _deduplicate_channels, prospect


class TestSignalsScoring:
    def test_score_topics_dark_factory(self):
        titles = ["Pushing My Dark Factory Further"]
        desc = ["autonomous coding pipeline"]
        score, hits = score_topics(titles, desc, [])
        assert score >= 20
        assert any(h.signal_name == "dark_factory" for h in hits)

    def test_score_topics_multi_signal_cap(self):
        titles = [
            "Building AI coding harnesses with multi-agent architecture",
            "Dark factory autonomous coding with Ollama local LLM",
            "MCP server integration for Claude Code agent framework",
        ]
        desc = ["context engineering beyond prompt engineering"]
        score, hits = score_topics(titles, desc, [])
        assert score <= 60  # cap at 60
        assert len(hits) >= 3

    def test_score_topics_no_match(self):
        score, hits = score_topics(["Cooking pasta tutorial"], [], [])
        assert score == 0
        assert hits == []

    def test_score_quality_all_pass(self):
        score, hits = score_quality(
            subscriber_count=5000,
            recent_video_days=7,
            has_technical_content=True,
            builds_in_public=True,
        )
        assert score == 40
        assert all(h.passed for h in hits)

    def test_score_quality_none_pass(self):
        score, hits = score_quality(
            subscriber_count=500,
            recent_video_days=60,
            has_technical_content=False,
            builds_in_public=False,
        )
        assert score == 0
        assert not any(h.passed for h in hits)

    def test_score_quality_partial(self):
        score, hits = score_quality(
            subscriber_count=2000,
            recent_video_days=15,
            has_technical_content=True,
            builds_in_public=False,
        )
        assert score == 30  # 3 signals pass

    def test_score_angles_coordination_ceiling(self):
        transcripts = ["hitting the coordination ceiling with single agent bottleneck"]
        score, hits = score_angles([], [], transcripts)
        assert score >= 15
        assert any(h.signal_name == "coordination_ceiling" for h in hits)

    def test_score_angles_infra_mentions(self):
        transcripts = ["using Supabase for persistence and NATS message bus"]
        score, hits = score_angles([], [], transcripts)
        assert score >= 15
        assert any(h.signal_name == "infra_mentions" for h in hits)

    def test_score_channel_full(self):
        fit = score_channel(
            video_titles=["Dark factory autonomous coding with multi-agent architecture"],
            video_descriptions=["Building AI coding harnesses with context engineering"],
            transcripts=["coordination ceiling single agent bottleneck supabase nats"],
            channel_description="AI coding tutorials",
            subscriber_count=50000,
            recent_video_days=5,
            has_technical_content=True,
            builds_in_public=True,
        )
        assert 0 <= fit.total <= 100
        assert fit.topic_score > 0
        assert fit.quality_score > 0
        assert fit.angle_score > 0
        assert len(fit.comment_angles) > 0

    def test_score_channel_zero(self):
        fit = score_channel()
        assert fit.total == 0
        assert fit.topic_score == 0
        assert fit.quality_score == 0
        assert fit.angle_score == 0

    def test_fit_score_to_dict(self):
        fit = score_channel(
            video_titles=["dark factory"],
            subscriber_count=1000,
            recent_video_days=10,
        )
        d = fit_score_to_dict(fit)
        assert "total_score" in d
        assert "topic_hits" in d
        assert isinstance(d["topic_hits"], list)

    def test_format_fit_report(self):
        fit = score_channel(video_titles=["dark factory"])
        report = format_fit_report(fit, "Test Channel")
        assert "Test Channel" in report
        assert "PMOVES Fit Report" in report


class TestInspector:
    def test_inspect_channel_basic(self):
        result = inspect_channel(
            channel_data={
                "id": "UCtest",
                "name": "Test Channel",
                "description": "AI coding harnesses and dark factory",
                "subscriber_count": 10000,
            },
            video_data=[
                {
                    "id": "v1",
                    "title": "Building AI Coding Harnesses That Ship",
                    "description": "dark factory autonomous coding",
                    "published_at": "2026-04-20T12:00:00Z",
                },
            ],
        )
        assert result["channel"]["name"] == "Test Channel"
        assert result["fit"]["total_score"] >= 0
        assert "report" in result
        assert "recommendations" in result

    def test_inspect_channel_string_sub_count(self):
        result = inspect_channel(
            channel_data={
                "id": "UCtest",
                "name": "Test",
                "subscriber_count": "50,000",
            },
        )
        assert result["channel"]["subscriber_count"] == 50000

    def test_detect_technical_depth(self):
        assert _detect_technical_depth(
            ["Build an API from scratch tutorial"],
            ["step by step guide to deploying"],
        ) is True
        assert _detect_technical_depth(
            ["Funny cat compilation"],
            [],
        ) is False

    def test_detect_builds_in_public(self):
        assert _detect_builds_in_public(
            ["Live coding stream: building a full app"],
            [],
        ) is True
        assert _detect_builds_in_public(
            ["News roundup this week"],
            [],
        ) is False


class TestCommenter:
    def test_draft_comments_dark_factory(self):
        result = draft_comments({
            "id": "test123",
            "title": "Pushing My Dark Factory Further with Kimi K2.6",
            "description": "A codebase that writes its own code, live",
            "channel_name": "Cole Medin",
        })
        assert len(result["drafts"]) >= 2
        assert result["specifics_found"] != ""
        assert "dark factory" in result["specifics_found"]
        for d in result["drafts"]:
            assert "text" in d
            assert "angle" in d
            assert len(d["text"]) > 50

    def test_draft_comments_generic(self):
        result = draft_comments({
            "id": "generic",
            "title": "My Thoughts on AI in 2026",
            "description": "A general overview of AI trends",
            "channel_name": "Some Channel",
        })
        assert len(result["drafts"]) >= 2
        for d in result["drafts"]:
            assert len(d["text"]) > 20

    def test_draft_comments_with_fit_result(self):
        fit_result = {
            "fit": {
                "comment_angles": [
                    "Dark factory -> PMOVES lattice: test angle",
                ],
            }
        }
        result = draft_comments(
            {"id": "x", "title": "dark factory video", "channel_name": "X"},
            fit_result=fit_result,
        )
        assert len(result["drafts"]) >= 2
        assert result["signal_angles"] != []

    def test_extract_video_specifics(self):
        specifics = _extract_video_specifics(
            "Building with Claude Code and Ollama",
            "Using MCP server for tool integration",
        )
        assert "claude code" in specifics
        assert "ollama" in specifics
        assert "mcp" in specifics

    def test_log_post_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from commenter import _ensure_log_dir
            result = log_post_result(
                video_id="test123",
                video_title="Test Video",
                channel_name="Test Channel",
                comment_text="Great video!",
                success=True,
                log_dir=Path(tmpdir),
            )
            assert result["status"] == "posted"
            assert result["logged"] is True
            log_file = Path(tmpdir) / "comment_log.jsonl"
            assert log_file.exists()
            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert entry["status"] == "posted"


class TestProspector:
    def test_deduplicate_channels(self):
        results = [
            {"id": "v1", "title": "Video 1", "channel": "Alice", "channel_id": "UC1"},
            {"id": "v2", "title": "Video 2", "channel": "Alice", "channel_id": "UC1"},
            {"id": "v3", "title": "Video 3", "channel": "Bob", "channel_id": "UC2"},
        ]
        channels = _deduplicate_channels(results)
        assert len(channels) == 2
        assert len(channels["UC1"]["videos"]) == 2
        assert len(channels["UC2"]["videos"]) == 1

    def test_deduplicate_no_channel_id(self):
        results = [
            {"id": "v1", "title": "V1", "channel": "Alice"},
            {"id": "v2", "title": "V2", "channel": "Bob"},
        ]
        channels = _deduplicate_channels(results)
        assert len(channels) == 2

    def test_prospect_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from inspector import load_config
            config = load_config()
            log_cfg = {"dir": tmpdir}

            search_results = [
                {
                    "id": "v1",
                    "title": "Building Multi-Agent AI Coding Harnesses",
                    "channel": "Tech Dev",
                    "channel_id": "UCtech",
                    "description": "dark factory autonomous coding with MCP",
                    "published_at": "2026-04-20T12:00:00Z",
                },
                {
                    "id": "v2",
                    "title": "Cooking Pasta Tutorial",
                    "channel": "Chef Bob",
                    "channel_id": "UCchef",
                    "description": "How to make pasta from scratch",
                    "published_at": "2026-04-18T10:00:00Z",
                },
            ]
            # Patch config logging dir
            import inspector as ins_mod
            orig_load = ins_mod.load_config
            def patched_load(*args, **kwargs):
                c = orig_load(*args, **kwargs)
                c["logging"]["dir"] = tmpdir
                return c
            ins_mod.load_config = patched_load

            try:
                result = prospect(
                    search_results=search_results,
                    query="AI multi-agent framework",
                    limit=5,
                )
                assert result["total_channels_found"] == 2
                assert result["channels_inspected"] == 2
                assert len(result["ranked_prospects"]) >= 1
                # Tech channel should rank higher than cooking channel
                if len(result["ranked_prospects"]) >= 2:
                    assert result["ranked_prospects"][0]["score"] >= result["ranked_prospects"][1]["score"]
            finally:
                ins_mod.load_config = orig_load


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
