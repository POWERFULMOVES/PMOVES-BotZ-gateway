"""
PMOVES-BoTZ Signal Scoring Engine

Scores YouTube channels against PMOVES.AI fit criteria.
Input: structured data from Agent Zero youtube_* tools.
Output: 0-100 fit score with signal breakdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# High-signal topics (each +20, cap 60)
TOPIC_SIGNALS = [
    {
        "name": "ai_coding_harness",
        "label": "Building AI coding harnesses / agent frameworks",
        "keywords": [
            "coding harness", "agent framework", "coding agent",
            "ai coding", "code generation pipeline", "automated coding",
            "claude code", "cursor ai", "windsurf", "copilot workspace",
            "archon", "claWZ", "aider", "continue.dev",
        ],
    },
    {
        "name": "multi_agent",
        "label": "Multi-agent architecture",
        "keywords": [
            "multi-agent", "agent fleet", "agent swarm", "agent lattice",
            "agent orchestration", "agent coordination", "distributed agents",
            "hierarchical agents", "meta-agent", "subordinate agent",
        ],
    },
    {
        "name": "dark_factory",
        "label": "Dark factory / autonomous coding pipelines",
        "keywords": [
            "dark factory", "autonomous coding", "zero human",
            "no human in the loop", "fully autonomous", "lights out coding",
            "autonomous pipeline", "self-coding", "codebase writes itself",
        ],
    },
    {
        "name": "context_engineering",
        "label": "Context engineering (beyond prompt engineering)",
        "keywords": [
            "context engineering", "context window", "context management",
            "context priming", "structured context", "context persistence",
            "beyond prompt engineering", "prompt engineering is dead",
        ],
    },
    {
        "name": "local_ai",
        "label": "Local AI / self-hosted models",
        "keywords": [
            "ollama", "local llm", "self-hosted", "run locally",
            "local inference", "lm studio", "kobold", "vllm",
            "dgx spark", "jetson", "home lab ai", "homelab",
        ],
    },
    {
        "name": "mcp_tools",
        "label": "MCP servers and tool integration",
        "keywords": [
            "mcp server", "mcp protocol", "model context protocol",
            "tool integration", "tool calling", "function calling",
            "mcp compatible", "mcp client",
        ],
    },
    {
        "name": "agent_ecosystem",
        "label": "Agent Zero, Claude Code, Cursor ecosystem",
        "keywords": [
            "agent zero", "claude code", "cursor", "windsurf",
            "coding assistant", "ai developer tool", "dev agent",
        ],
    },
]

# Channel quality signals (each +10)
QUALITY_SIGNALS = [
    {
        "name": "active_creator",
        "label": "Active creator (video in last 30 days)",
        "check": "recent_video_days",
        "threshold": 30,
    },
    {
        "name": "subscriber_base",
        "label": "1K+ subscribers",
        "check": "subscriber_count",
        "threshold": 1000,
    },
    {
        "name": "technical_depth",
        "label": "Technical depth (not just news recap)",
        "check": "has_technical_content",
    },
    {
        "name": "builds_in_public",
        "label": "Builds in public (shows actual code/workflows)",
        "check": "builds_in_public",
    },
]

# PMOVES angle signals (each +15)
ANGLE_SIGNALS = [
    {
        "name": "coordination_ceiling",
        "label": "Mentions hitting coordination ceiling with single agent",
        "keywords": [
            "coordination ceiling", "single agent bottleneck",
            "cannot scale one agent", "agent overhead",
            "too many handoffs", "sequential bottleneck",
            "one agent cannot handle", "hitting the limit",
        ],
    },
    {
        "name": "memory_context_problems",
        "label": "Discusses agent memory / context management problems",
        "keywords": [
            "context overflow", "memory problem", "forgetting context",
            "context window limit", "long context", "context window too small",
            "losing context", "context management", "rag limitations",
            "flat embeddings", "embedding limitations",
        ],
    },
    {
        "name": "scaling_workflows",
        "label": "Talks about scaling agent workflows",
        "keywords": [
            "scale agent", "scaling workflow", "production agent",
            "agent at scale", "enterprise agent", "fleet of agents",
            "multiple agents working", "parallel agents",
        ],
    },
    {
        "name": "infra_mentions",
        "label": "Mentions Supabase, NATS, or similar infra",
        "keywords": [
            "supabase", "nats", "message bus", "event bus",
            "postgres", "redis", "kafka", "rabbitmq",
            "docker compose", "kubernetes", "infrastructure",
        ],
    },
]

PMOVES_VALUE_PROP = (
    "PMOVES.AI is a Metal-Organic Framework architecture for distributed machine intelligence. "
    "Key differentiators: Multi-agent lattice with structural coherence, "
    "CHIT geometric information encoding (Poincare disk, not flat embeddings), "
    "NATS message bus for inter-agent communication, "
    "Hardware-aware profiles for DGX Spark, workstation, laptop. "
    "Complementary to Archon: harness for one agent vs lattice for a fleet. "
    "Brand voice: physics-first, evidence-based, attractor not brand, Ghostbusters energy. Never spammy."
)


@dataclass
class TopicHit:
    signal_name: str
    label: str
    matched_keywords: list[str]
    score: int


@dataclass
class QualityHit:
    signal_name: str
    label: str
    passed: bool
    score: int


@dataclass
class AngleHit:
    signal_name: str
    label: str
    matched_keywords: list[str]
    score: int


@dataclass
class FitScore:
    total: int
    topic_score: int
    quality_score: int
    angle_score: int
    topic_hits: list[TopicHit] = field(default_factory=list)
    quality_hits: list[QualityHit] = field(default_factory=list)
    angle_hits: list[AngleHit] = field(default_factory=list)
    comment_angles: list[str] = field(default_factory=list)


def _match_keywords(text: str, keywords: list[str]) -> list[str]:
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def score_topics(
    video_titles: list[str],
    video_descriptions: list[str],
    transcripts: list[str],
    channel_description: str = "",
) -> tuple[int, list[TopicHit]]:
    combined = " ".join(video_titles + video_descriptions + transcripts + [channel_description])
    hits: list[TopicHit] = []
    raw = 0
    for sig in TOPIC_SIGNALS:
        matched = _match_keywords(combined, sig["keywords"])
        if matched:
            raw += 20
            hits.append(TopicHit(
                signal_name=sig["name"],
                label=sig["label"],
                matched_keywords=matched,
                score=20,
            ))
    return min(raw, 60), hits


def score_quality(
    subscriber_count: int = 0,
    recent_video_days: Optional[int] = None,
    has_technical_content: bool = False,
    builds_in_public: bool = False,
) -> tuple[int, list[QualityHit]]:
    checks = {
        "recent_video_days": recent_video_days,
        "subscriber_count": subscriber_count,
        "has_technical_content": has_technical_content,
        "builds_in_public": builds_in_public,
    }
    hits: list[QualityHit] = []
    raw = 0
    for sig in QUALITY_SIGNALS:
        check_key = sig["check"]
        val = checks.get(check_key)
        passed = False
        if check_key == "recent_video_days" and val is not None:
            passed = val <= sig["threshold"]
        elif check_key == "subscriber_count" and val is not None:
            passed = val >= sig["threshold"]
        elif check_key in ("has_technical_content", "builds_in_public") and val is not None:
            passed = bool(val)
        if passed:
            raw += 10
        hits.append(QualityHit(
            signal_name=sig["name"],
            label=sig["label"],
            passed=passed,
            score=10 if passed else 0,
        ))
    return min(raw, 40), hits


def score_angles(
    video_titles: list[str],
    video_descriptions: list[str],
    transcripts: list[str],
) -> tuple[int, list[AngleHit]]:
    combined = " ".join(video_titles + video_descriptions + transcripts)
    hits: list[AngleHit] = []
    raw = 0
    for sig in ANGLE_SIGNALS:
        matched = _match_keywords(combined, sig["keywords"])
        if matched:
            raw += 15
            hits.append(AngleHit(
                signal_name=sig["name"],
                label=sig["label"],
                matched_keywords=matched,
                score=15,
            ))
    return min(raw, 60), hits


def compute_comment_angles(fit: FitScore) -> list[str]:
    angles: list[str] = []
    topic_names = {h.signal_name for h in fit.topic_hits}
    angle_names = {h.signal_name for h in fit.angle_hits}

    if "dark_factory" in topic_names:
        angles.append(
            "Dark factory -> PMOVES lattice: "
            "You built the dark factory for one node. "
            "We scale it across a fleet with geometric-encoded context."
        )
    if "multi_agent" in topic_names or "scaling_workflows" in angle_names:
        angles.append(
            "Multi-agent scaling -> MOF lattice: "
            "Single-agent pipelines hit coordination ceilings. "
            "A metal-organic framework gives structural coherence to agent fleets."
        )
    if "context_engineering" in topic_names or "memory_context_problems" in angle_names:
        angles.append(
            "Context engineering -> CHIT: "
            "Flat embeddings destroy hierarchical structure. "
            "Poincare disk encoding preserves it."
        )
    if "mcp_tools" in topic_names or "infra_mentions" in angle_names:
        angles.append(
            "MCP/infra -> NATS geometry bus: "
            "MCP for tool integration, NATS for inter-agent coordination. "
            "Different layers, same insight."
        )
    if "ai_coding_harness" in topic_names:
        angles.append(
            "Harness -> MOF pore: "
            "A harness wraps one agent. A MOF pore sits at a lattice node. "
            "Same pattern, distributed."
        )
    if "coordination_ceiling" in angle_names:
        angles.append(
            "Coordination ceiling -> lattice geometry: "
            "Sequential handoffs are the bottleneck. Crystal-structure coordination, not pipeline."
        )
    if "local_ai" in topic_names:
        angles.append(
            "Local AI -> hardware-aware profiles: "
            "DGX Spark, workstation, laptop -- the lattice adapts to what you have."
        )

    if not angles:
        angles.append(
            "General PMOVES awareness: "
            "Interesting work on agent infrastructure. "
            "We are exploring distributed agent lattices with geometric context encoding."
        )

    return angles


def score_channel(
    video_titles: list[str] = None,
    video_descriptions: list[str] = None,
    transcripts: list[str] = None,
    channel_description: str = "",
    subscriber_count: int = 0,
    recent_video_days: Optional[int] = None,
    has_technical_content: bool = False,
    builds_in_public: bool = False,
) -> FitScore:
    video_titles = video_titles or []
    video_descriptions = video_descriptions or []
    transcripts = transcripts or []

    topic_score, topic_hits = score_topics(
        video_titles, video_descriptions, transcripts, channel_description
    )
    quality_score, quality_hits = score_quality(
        subscriber_count, recent_video_days, has_technical_content, builds_in_public
    )
    angle_score, angle_hits = score_angles(
        video_titles, video_descriptions, transcripts
    )

    raw_total = topic_score * 0.4 + quality_score * 0.25 + angle_score * 0.35
    total = min(int(round(raw_total)), 100)

    fit = FitScore(
        total=total,
        topic_score=topic_score,
        quality_score=quality_score,
        angle_score=angle_score,
        topic_hits=topic_hits,
        quality_hits=quality_hits,
        angle_hits=angle_hits,
    )
    fit.comment_angles = compute_comment_angles(fit)
    return fit


def fit_score_to_dict(fit: FitScore) -> dict:
    return {
        "total_score": fit.total,
        "topic_score": fit.topic_score,
        "quality_score": fit.quality_score,
        "angle_score": fit.angle_score,
        "topic_hits": [
            {"signal": h.signal_name, "label": h.label, "keywords": h.matched_keywords, "score": h.score}
            for h in fit.topic_hits
        ],
        "quality_hits": [
            {"signal": h.signal_name, "label": h.label, "passed": h.passed, "score": h.score}
            for h in fit.quality_hits
        ],
        "angle_hits": [
            {"signal": h.signal_name, "label": h.label, "keywords": h.matched_keywords, "score": h.score}
            for h in fit.angle_hits
        ],
        "comment_angles": fit.comment_angles,
    }


def format_fit_report(fit: FitScore, channel_name: str = "Unknown") -> str:
    lines = [
        f"# PMOVES Fit Report: {channel_name}",
        f"**Total Score: {fit.total}/100**",
        "",
        "## Signal Breakdown",
        f"- Topic Score: {fit.topic_score}/60",
        f"- Quality Score: {fit.quality_score}/40",
        f"- Angle Score: {fit.angle_score}/60",
        "",
    ]
    if fit.topic_hits:
        lines.append("### Topic Signals Hit")
        for h in fit.topic_hits:
            kw_str = ", ".join(h.matched_keywords[:3])
            lines.append(f"- [x] {h.label} (+{h.score}) -- matched: {kw_str}")
        lines.append("")
    lines.append("### Quality Signals")
    for h in fit.quality_hits:
        icon = "[x]" if h.passed else "[ ]"
        lines.append(f"- {icon} {h.label} (+{h.score})")
    lines.append("")
    if fit.angle_hits:
        lines.append("### PMOVES Angle Signals Hit")
        for h in fit.angle_hits:
            kw_str = ", ".join(h.matched_keywords[:3])
            lines.append(f"- [x] {h.label} (+{h.score}) -- matched: {kw_str}")
        lines.append("")
    if fit.comment_angles:
        lines.append("### Recommended Comment Angles")
        for i, angle in enumerate(fit.comment_angles, 1):
            lines.append(f"{i}. {angle}")
        lines.append("")
    return "\n".join(lines)
