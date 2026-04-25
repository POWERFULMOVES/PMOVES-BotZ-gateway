"""
PMOVES-BoTZ Comment Drafting & Posting

Generates contextual comment drafts and logs post attempts.
Designed to be called BY Agent Zero — posting uses youtube_comment tool externally.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from signals import PMOVES_VALUE_PROP


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


def _log_comment(
    video_id: str,
    video_title: str,
    channel_name: str,
    comment_text: str,
    status: str,
    error: str = "",
    log_dir: Path | None = None,
):
    d = _ensure_log_dir(log_dir)
    log_file = d / "comment_log.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "video_id": video_id,
        "video_title": video_title,
        "channel_name": channel_name,
        "comment_text": comment_text,
        "status": status,  # drafted, posted, failed
        "error": error,
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _extract_video_specifics(title: str, description: str, transcript: str = "") -> str:
    """Pull out specific references from video content for comment grounding."""
    specifics = []
    combined = f"{title} {description} {transcript}"

    # Look for tool/model names
    import re
    tool_patterns = [
        r"Claude Code", r"Cursor", r"Windsurf", r"Agent Zero", r"Archon",
        r"Ollama", r"Kimi", r"GPT-4", r"GPT-5", r"Gemini", r"Llama",
        r"Supabase", r"NATS", r"MCP", r"Docker", r"Kubernetes",
        r"DGX Spark", r"Nemotron", r"Qwen", r"Gemma",
    ]
    for pat in tool_patterns:
        if re.search(pat, combined, re.IGNORECASE):
            specifics.append(pat.lower())

    # Look for specific concepts mentioned
    concept_patterns = [
        r"dark factory", r"context engineering", r"multi-agent",
        r"coding harness", r"knowledge base", r"RAG",
        r"long.term memory", r"error recovery", r"task delegation",
        r"live coding", r"from scratch", r"autonomous",
    ]
    for pat in concept_patterns:
        if re.search(pat, combined, re.IGNORECASE):
            specifics.append(pat.lower())

    return ", ".join(set(specifics))


def draft_comments(
    video_data: dict,
    fit_result: dict | None = None,
 config_path: str | Path | None = None,
) -> dict:
    """
    Generate 2-3 contextual comment drafts for a video.

    Args:
        video_data: Dict with video info, e.g.:
            {
                "id": "BGpYeE1dKI8",
                "title": "Pushing My Dark Factory Further...",
                "description": "...",
                "channel_name": "Cole Medin",
            }
        fit_result: Optional result from inspector.inspect_channel for signal-aware drafting.
        config_path: Optional path to config.yaml.

    Returns:
        Dict with list of draft comments and metadata.
    """
    config = load_config(config_path)
    comment_config = config.get("comment", {})
    max_drafts = comment_config.get("max_drafts", 3)
    name_drop = comment_config.get("pmoves_name_drop", False)
    tone = comment_config.get("tone", "")

    video_id = video_data.get("id", "unknown")
    title = video_data.get("title", "")
    description = video_data.get("description", "")
    channel_name = video_data.get("channel_name", video_data.get("channel", "Unknown"))
    transcript = video_data.get("transcript", "")

    specifics = _extract_video_specifics(title, description, transcript)

    # Extract signal angles from fit result if available
    angles = []
    if fit_result:
        angles = fit_result.get("fit", {}).get("comment_angles", [])

    drafts = []

    # Draft 1: Direct technical engagement (always generated)
    d1 = _draft_technical_engagement(title, specifics, channel_name, name_drop)
    drafts.append(d1)

    # Draft 2: Signal-aware angle (if signals available)
    if angles:
        d2 = _draft_signal_angle(angles[0], title, specifics, channel_name, name_drop)
        drafts.append(d2)

    # Draft 3: Question-based engagement
    d3 = _draft_question_engagement(title, specifics, channel_name, name_drop)
    drafts.append(d3)

    # Trim to max_drafts
    drafts = drafts[:max_drafts]

    # Log drafts
    log_dir = Path(__file__).parent / config.get("logging", {}).get("dir", "logs")
    for d in drafts:
        _log_comment(video_id, title, channel_name, d["text"], "drafted", log_dir=log_dir)

    return {
        "video_id": video_id,
        "video_title": title,
        "channel_name": channel_name,
        "specifics_found": specifics,
        "signal_angles": angles,
        "drafts": drafts,
        "tone_guidance": tone,
    }


def _draft_technical_engagement(
    title: str, specifics: str, channel_name: str, name_drop: bool
) -> dict:
    """Draft 1: Direct technical engagement referencing specific content."""
    parts = []

    # Opening that references the video topic
    if "dark factory" in specifics:
        parts.append(
            "The dark factory pattern is exactly where autonomous coding converges -- "
            "one agent generating code that another executes, with minimal human in the loop. "
            "Seeing this pushed live is a great stress test for that pipeline."
        )
    elif "coding harness" in specifics or "context engineering" in specifics:
        parts.append(
            "The evolution from prompt engineering to context engineering is the real inflection point. "
            "Structuring the environment the agent operates in, rather than optimizing individual prompts, "
            "changes the entire reliability curve."
        )
    elif "multi-agent" in specifics:
        parts.append(
            "Multi-agent coordination is where the interesting physics lives. "
            "Single-agent pipelines work for well-bounded tasks, but the coordination overhead "
            "scales non-linearly as you add specialization."
        )
    elif specifics:
        parts.append(
            f"Really interesting work with {specifics.split(',')[0]}. "
            "The agent infrastructure space is moving fast and it is good to see "
            "people pushing beyond the basic wrapper pattern."
        )
    else:
        parts.append(
            f"Great video on this. The details matter here -- "
            "the gap between demo and production agent workflows is where "
            "most of the interesting problems live."
        )

    # PMOVES angle (subtle, not first sentence)
    if name_drop:
        parts.append(
            "We have been exploring a Metal-Organic Framework approach where agents "
            "sit at lattice nodes with geometric-encoded context (Poincare disk embeddings) "
            "so inter-agent handoff does not lose structural information."
        )
    else:
        if "dark factory" in specifics:
            parts.append(
                "The question that keeps coming up: at what point does the coordination overhead "
                "of chaining single-agent loops exceed the cost of running a structured multi-agent lattice? "
                "When you are generating, reviewing, testing, and committing -- that is already "
                "four coordination handoffs through what is essentially a sequential bottleneck."
            )
        elif "context engineering" in specifics or "rag" in specifics:
            parts.append(
                "One thing we found: flat vector embeddings destroy hierarchical relationships "
                "in documentation. Hyperbolic geometry (Poincare disk) preserves the tree structure "
                "that makes RAG actually useful for codebases."
            )
        else:
            parts.append(
                "The coordination ceiling is the constraint that does not get enough attention. "
                "Sequential handoffs between agent steps create a pipeline bottleneck that "
                "crystal-structure coordination (lattice topology, not linear chain) can bypass."
            )

    return {
        "angle": "technical_engagement",
        "text": " ".join(parts),
        "references_specifics": bool(specifics),
    }


def _draft_signal_angle(
    angle: str, title: str, specifics: str, channel_name: str, name_drop: bool
) -> dict:
    """Draft 2: Based on a specific PMOVES signal angle."""
    parts = []

    if "dark factory" in angle.lower():
        parts.append(
            f"This is the frontier. The dark factory for one node is hard enough -- "
            f"scaling it across a fleet with geometric-encoded context is where it gets "
            f"structurally interesting. Crystal-structure coordination vs pipeline coordination."
        )
    elif "multi-agent" in angle.lower() or "lattice" in angle.lower():
        parts.append(
            "A metal-organic framework for agent coordination gives structural coherence "
            "to a fleet -- each agent at a lattice node with typed message passing. "
            "The geometry of the coordination graph matters as much as the intelligence of individual nodes."
        )
    elif "context" in angle.lower() or "chit" in angle.lower() or "embedding" in angle.lower():
        parts.append(
            "Context engineering with flat embeddings is like doing physics in one dimension. "
            "Poincare disk embeddings preserve the hierarchical structure that makes "
            "agent context actually useful across handoffs."
        )
    elif "mcp" in angle.lower() or "nats" in angle.lower():
        parts.append(
            "MCP solves tool integration, but the harder problem is inter-agent context transfer. "
            "NATS with typed schemas gives you the message bus, but you still need "
            "geometric encoding to prevent information loss at each hop."
        )
    elif "harness" in angle.lower() or "pore" in angle.lower():
        parts.append(
            "The harness pattern and the MOF pore pattern are isomorphic -- same insight, "
            "different scale. A harness wraps one agent with structure. A pore places that "
            "structured agent at a node in a distributed lattice."
        )
    else:
        parts.append(
            f"This connects to something we have been exploring -- distributed agent lattices "
            f"where the coordination topology is a crystal structure rather than a pipeline. "
            f"Different problem framing, same underlying physics."
        )

    if name_drop:
        parts.append(
            "PMOVES.AI implements this as a Metal-Organic Framework architecture with "
            "CHIT geometric encoding and NATS inter-agent bus."
        )

    return {
        "angle": f"signal: {angle.split(':')[0].strip() if ':' in angle else angle[:50]}",
        "text": " ".join(parts),
        "references_specifics": bool(specifics),
    }


def _draft_question_engagement(
    title: str, specifics: str, channel_name: str, name_drop: bool
) -> dict:
    """Draft 3: Question-based, invites dialogue."""
    parts = []

    if "dark factory" in specifics:
        parts.append(
            "Curious about your error recovery in the dark factory pipeline. "
            "When Claude fails mid-task, do you re-structure the context before retrying, "
            "or just feed the error back raw?"
        )
        parts.append(
            "We found that context enrichment on failure (adding relevant knowledge base entries "
            "before the retry) cuts error recurrence by roughly half compared to raw error feedback."
        )
    elif "multi-agent" in specifics or "agent" in specifics:
        parts.append(
            "Have you hit the coordination ceiling yet? The point where adding more agent "
            "specialization increases overhead faster than it increases throughput?"
        )
        parts.append(
            "In our testing, switching from sequential pipeline to lattice topology "
            "(parallel agents at crystal nodes) broke through that ceiling around 4 agents."
        )
    elif "context engineering" in specifics or "knowledge base" in specifics or "rag" in specifics:
        parts.append(
            "How are you handling the embedding dimensionality problem? "
            "As your knowledge base grows, flat embeddings start losing the hierarchical "
            "relationships between documents."
        )
        parts.append(
            "Hyperbolic embeddings (Poincare disk) preserve tree structure natively -- "
            "worth exploring if your RAG queries are hitting relevance walls at scale."
        )
    else:
        parts.append(
            "What is the hardest failure mode you have hit with this approach? "
            "The edge cases that look fine in a 10-minute demo but break "
            "at production scale are always the interesting ones."
        )

    if name_drop:
        parts.append(
            "PMOVES.AI tracks failure modes through CHIT signed provenance -- "
            "Merkle proofs on context chains so you can trace exactly where information was lost."
        )

    return {
        "angle": "question_engagement",
        "text": " ".join(parts),
        "references_specifics": bool(specifics),
    }


def log_post_result(
    video_id: str,
    video_title: str,
    channel_name: str,
    comment_text: str,
    success: bool,
    error: str = "",
    config_path: str | Path | None = None,
    log_dir: Path | None = None,
) -> dict:
    """
    Log the result of a comment post attempt.
    Call this AFTER Agent Zero attempts youtube_comment.

    Returns:
        Dict with logged entry.
    """
    if log_dir is None:
        config = load_config(config_path)
        log_dir = Path(__file__).parent / config.get("logging", {}).get("dir", "logs")
    status = "posted" if success else "failed"
    _log_comment(video_id, video_title, channel_name, comment_text, status, error, log_dir)
    return {
        "video_id": video_id,
        "status": status,
        "error": error,
        "logged": True,
    }


def format_drafts_output(result: dict) -> str:
    """Format draft comments for terminal output."""
    lines = [
        f"# Comment Drafts: {result['video_title']}",
        f"Channel: {result['channel_name']}",
        f"Specifics found: {result['specifics_found'] or 'none'}",
        "",
    ]
    for i, d in enumerate(result["drafts"], 1):
        lines.append(f"## Draft {i} ({d['angle']})")
        lines.append(d["text"])
        lines.append("")
    if result.get("tone_guidance"):
        lines.append(f"Tone: {result['tone_guidance']}")
    return "\n".join(lines)
