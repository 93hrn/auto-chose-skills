"""auto-chose-skill — every-turn routing nudge + the detailed skill.

The hook is the only Hermes mechanism that runs on *every* turn (skills are
just index entries in the system prompt). Keep the injected text short: it is
paid on every LLM call, next to Ponytail's ~5 KB block.
"""
from __future__ import annotations

from typing import Any

_CORE = (
    "ROUTER (silent): before acting on a non-trivial task, name its type in one line, "
    "then check <available_skills>. One skill fits -> skill_view it and follow it, "
    "no announcement, no permission ask, no rescan of the skills dir. Two only when "
    "they are sequential phases. Nothing fits -> do it natively, do not search twice. "
    "Never load a skill just to compare it. Safety/approval rules still apply."
)
_EXPLAIN_SUFFIX = ' Trace on: start your reply with one line "-> <skill or native>".'

_explain = False   # process-scoped, like Ponytail's mode: resets on restart


def _pre_llm_call(session_id: str = "", **_: Any) -> dict[str, str]:
    text = _CORE + (_EXPLAIN_SUFFIX if _explain else "")
    return {"context": text}


def _handle_command(raw_args: str) -> str:
    """`/auto-chose [explain|silent|status]`."""
    global _explain
    arg = (raw_args or "").strip().lower()
    if arg in ("explain", "on", "trace"):
        _explain = True
        return "auto-chose: trace ON (this process only)."
    if arg in ("silent", "off", "quiet"):
        _explain = False
        return "auto-chose: silent."
    return (f"auto-chose: {'trace ON' if _explain else 'silent'}. "
            "Usage: /auto-chose [explain|silent|status]")


def register(ctx: Any) -> None:
    """Register the pre-LLM hook and the /auto-chose command.

    技能本身装在 skills/auto-chose/auto-chose-skill（普通本地技能），
    这样不重启也能用；插件只负责每轮那句提醒。
    """
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_command(
        "auto-chose",
        _handle_command,
        description="Toggle auto-chose-skill trace: explain or silent.",
        args_hint="[explain|silent|status]",
    )
