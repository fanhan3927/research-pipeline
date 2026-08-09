"""快速查看一个项目目前跑到哪、卡在哪个暂停点。

audit_log.md 是只追加的流水账（这是刻意的设计——保持简单、方便审计，
不做成一个需要维护状态转换的结构化状态机）。这个脚本不试图"智能"推断
"是否已解决"，只是把目录完成情况和历史上出现过的暂停记录整理出来，
让人一眼看清楚，自己判断当前卡在哪一步。

用法：
    python scripts/project_status.py --project-dir projects/xxx_20260809
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SUBDIR_LABELS = {
    "00_raw": "原始材料",
    "01_triage": "分发链：研判结论",
    "02_processing": "分发链：加工层产物",
    "03_pipeline": "分发链：Pipeline 内外部版",
    "04_forensics": "研发链：材料证伪",
    "05_screening": "研发链：定性研判",
    "06_valuation": "研发链：估值报告",
    "07_report": "研发链：报告/大纲",
}

LOG_ROW_RE = re.compile(
    r"^\|\s*(?P<time>[^|]+?)\s*\|\s*(?P<actor>[^|]+?)\s*\|\s*(?P<step>[^|]+?)\s*\|"
    r"\s*(?P<pause_type>[^|]+?)\s*\|\s*(?P<detail>.*?)\s*\|$"
)


def _dir_summary(project_dir: Path) -> list[str]:
    lines = []
    for sub, label in SUBDIR_LABELS.items():
        sub_path = project_dir / sub
        if not sub_path.exists():
            continue
        n_files = sum(1 for p in sub_path.rglob("*") if p.is_file())
        status = f"{n_files} 个文件" if n_files else "空（尚未产出）"
        lines.append(f"  {sub:<14} {label:<16} {status}")
    return lines


def _parse_log(project_dir: Path) -> list[dict]:
    log_path = project_dir / "audit_log.md"
    if not log_path.exists():
        return []
    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---") or "时间" in line and "执行方" in line:
            continue
        m = LOG_ROW_RE.match(line)
        if m:
            rows.append(m.groupdict())
    return rows


def print_status(project_dir: Path) -> None:
    if not project_dir.exists():
        print(f"项目目录不存在：{project_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"项目：{project_dir.name}\n")
    print("目录完成情况：")
    for line in _dir_summary(project_dir):
        print(line)

    rows = _parse_log(project_dir)
    pauses = [r for r in rows if r["pause_type"] in ("confirm", "external_wait")]

    print(f"\n历史暂停记录（人工确认 / 外部等待），按时间顺序，共 {len(pauses)} 条：")
    if not pauses:
        print("  （无）")
    else:
        for r in pauses:
            label = "人工确认" if r["pause_type"] == "confirm" else "外部等待"
            print(f"  [{r['time']}] ({label}) {r['step']} — {r['detail']}")
        print(
            "\n最下面一条如果找不到对应的「已确认/已收到回复」记录，通常说明流程目前卡在这里；"
            "本脚本不做自动判断，需要你自己对照 audit_log.md 全文确认。"
        )

    if rows:
        last = rows[-1]
        print(f"\n最近一条操作：[{last['time']}] {last['actor']} · {last['step']}")


def _main() -> None:
    parser = argparse.ArgumentParser(description="查看项目当前进度")
    parser.add_argument("--project-dir", required=True, type=Path)
    args = parser.parse_args()
    print_status(args.project_dir)


if __name__ == "__main__":
    _main()
