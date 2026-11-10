#!/usr/bin/env python3
"""安装 auto-chose-skill（技能 + 插件）。纯标准库，Windows / macOS / Linux 通用。

    python install.py                     # 自动找 HERMES_HOME 或 ~/.hermes
    python install.py --hermes-home DIR   # 指定 Hermes 根目录
    python install.py --dry-run           # 只看会做什么
    python install.py --force             # 覆盖已装版本
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parent
SKILL_SRC = PKG / "skills" / "auto-chose-skill"
PLUGIN_SRC = PKG / "plugin"


def default_home() -> pathlib.Path:
    env = os.environ.get("HERMES_HOME")
    return pathlib.Path(env) if env else pathlib.Path.home() / ".hermes"


def looks_like_hermes(home: pathlib.Path) -> bool:
    return (home / "config.yaml").is_file() or (home / "skills").is_dir()


def main() -> int:
    ap = argparse.ArgumentParser(description="安装 auto-chose-skill")
    ap.add_argument("--hermes-home", help="Hermes 根目录（默认 $HERMES_HOME 或 ~/.hermes）")
    ap.add_argument("--force", action="store_true", help="覆盖已存在版本")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    args = ap.parse_args()

    home = pathlib.Path(args.hermes_home).expanduser() if args.hermes_home else default_home()
    skill_dst = home / "skills" / "auto-chose" / "auto-chose-skill"
    plugin_dst = home / "plugins" / "auto-chose-skill"

    print(f"Hermes 根目录: {home}")
    if not looks_like_hermes(home):
        print("  警告: 这里没有 config.yaml 也没有 skills/ 目录 —— 确认 Hermes 装过？", file=sys.stderr)
        print("  继续安装，但很可能装错位置。用 --hermes-home 指定真实根目录。", file=sys.stderr)
    if not SKILL_SRC.joinpath("SKILL.md").is_file():
        print(f"包不完整：找不到 {SKILL_SRC / 'SKILL.md'}", file=sys.stderr)
        return 1

    for src, dst, label in ((SKILL_SRC, skill_dst, "技能"), (PLUGIN_SRC, plugin_dst, "插件")):
        if dst.exists() and not args.force:
            print(f"  跳过{label}（已存在，加 --force 覆盖）: {dst}")
            continue
        print(f"  安装{label}: {dst}")
        if args.dry_run:
            continue
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)

    if args.dry_run:
        print("\n(dry-run：没有写任何文件)")
        return 0

    enabled = False
    try:
        r = subprocess.run(["hermes", "plugins", "enable", "auto-chose-skill"],
                           capture_output=True, text=True, timeout=60)
        enabled = r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        enabled = False

    print()
    if enabled:
        print("插件已启用。")
    else:
        print("插件已复制，但没能自动启用（hermes 不在 PATH？）。手动执行一次：")
        print("  hermes plugins enable auto-chose-skill")
    print("接下来：重启 Hermes（桌面端退出重开，或 hermes gateway restart），")
    print("让每轮提醒生效；只想要技能的话，现在就能用 /auto-chose-skill。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
