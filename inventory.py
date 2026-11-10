#!/usr/bin/env python3
"""List what is actually installed and callable: skills on disk + skills provided by plugins.

    python inventory.py                # 表格：名字 / 分类 / 一句话 / 标记
    python inventory.py --grep ppt     # 只留匹配名字或描述的
    python inventory.py --json         # 带 path，便于直接 read_file
    python inventory.py --selftest     # 解析器自检（无断言通过则退出码非 0）

不用 Hermes 的 python 依赖，纯标准库；上百个技能实测 ~0.1 s，所以不缓存。
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time

HOME = pathlib.Path(os.environ.get("HERMES_HOME") or (pathlib.Path.home() / ".hermes"))
CURRENT = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
SKILLS = HOME / "skills"
PLUGINS = HOME / "plugins"


def fields(text: str) -> dict:
    """取 frontmatter 顶层标量（只认这几个键，避免引入 YAML 依赖）。"""
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}
    raw = m.group(1)
    out: dict[str, str] = {}
    for key in ("name", "description", "platforms", "disable-model-invocation"):
        mm = re.search(rf"^{key}:\s*(.+)$", raw, re.M)
        if mm:
            out[key] = mm.group(1).strip()
    # description 可能是块标量
    bm = re.search(r"^description:\s*[>|]-?\s*\n((?:[ \t]+.*\n?)+)", raw, re.M)
    if bm:
        out["description"] = " ".join(x.strip() for x in bm.group(1).splitlines())
    return out


def one_line(desc: str, limit: int = 74) -> str:
    desc = re.sub(r"\s+", " ", desc or "").strip().strip('"').strip("'")
    first = re.split(r"(?<=[。；;])\s*|\.\s+(?=[A-Z])", desc)[0] if desc else ""
    return (first or desc)[:limit] + ("…" if len(first or desc) > limit else "")


def scan_skills() -> list[dict]:
    rows: list[dict] = []
    for p in sorted(SKILLS.rglob("SKILL.md")):
        rel = p.relative_to(SKILLS)
        if any(seg.startswith(".") for seg in rel.parts):
            continue
        f = fields(p.read_text(encoding="utf-8", errors="replace"))
        if not f.get("name"):
            continue
        rows.append({
            "name": f["name"].strip('"').strip("'"),
            "category": rel.parts[0] if len(rel.parts) > 1 else "(root)",
            "desc": one_line(f.get("description", "")),
            "platforms": f.get("platforms", ""),
            "manual_only": "disable-model-invocation" in f,
            "path": str(p),
        })
    return rows


def scan_plugins() -> list[dict]:
    """插件提供的技能：ponytail 那 6 个就是走这条路的，磁盘上不在 skills/ 里。"""
    rows: list[dict] = []
    for p in sorted(PLUGINS.glob("*/plugin.yaml")):
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        name = re.search(r"^name:\s*(.+)$", txt, re.M)
        if not name:
            continue
        block = re.search(r"^provides_skills:\s*\n((?:[ \t]+-.*\n?)+)", txt, re.M)
        if not block:
            continue
        pname = name.group(1).strip()
        for item in re.findall(r"-\s*(\S+)", block.group(1)):
            skill_md = None
            for cand in (p.parent / "skills" / item / "SKILL.md", p.parent / item / "SKILL.md"):
                if cand.is_file():
                    skill_md = cand
                    break
            desc = ""
            if skill_md:
                desc = one_line(fields(skill_md.read_text(encoding="utf-8", errors="replace")).get("description", ""))
            rows.append({"name": f"{pname}:{item}", "category": "plugin", "desc": desc,
                         "platforms": "", "manual_only": False,
                         "path": str(skill_md or p)})
    return rows


def main() -> int:
    args = sys.argv[1:]
    t0 = time.perf_counter()
    skills = scan_skills()
    plugins = scan_plugins()
    elapsed = time.perf_counter() - t0

    if "--selftest" in args:
        assert skills, "一个技能都没解析到，HERMES_HOME 或解析器有问题"
        assert all(r["name"] and r["path"] for r in skills), "有空名字/空路径"
        names = [r["name"] for r in skills]
        assert len(set(names)) == len(names), "技能名重复，路由会歧义"
        assert sum(1 for r in skills if r["desc"]) > len(skills) * 0.9, "描述解析率过低"
        print(f"selftest OK: {len(skills)} skills, {len(plugins)} plugin skills, {elapsed:.3f}s")
        return 0

    rows = skills + plugins
    terms: list[str] = []
    if "--grep" in args:
        raw = args[args.index("--grep") + 1] if len(args) > args.index("--grep") + 1 else ""
        terms = [t.strip().lower() for t in re.split(r"[|,]", raw) if t.strip()]
    if terms:
        def hit(row: dict) -> bool:
            blob = (row["name"] + " " + row["desc"]).lower()
            for t in terms:
                # 英文按词边界（否则 figure 会命中 configure），中文按子串
                if t.isascii():
                    if re.search(rf"\b{re.escape(t)}", blob):
                        return True
                elif t in blob:
                    return True
            return False
        rows = [r for r in rows if hit(r)]

    if "--json" in args:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0

    print(f"{len(skills)} skills + {len(plugins)} plugin skills  ({elapsed:.2f}s)")
    for r in sorted(rows, key=lambda x: (x["category"], x["name"])):
        flags = []
        if r["platforms"] and CURRENT not in r["platforms"]:
            flags.append("!" + r["platforms"].strip("[]"))
        if r["manual_only"]:
            flags.append("manual")
        tail = ("  [" + ",".join(flags) + "]") if flags else ""
        print(f"  {r['name']:<28} {r['category']:<20} {r['desc']}{tail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
