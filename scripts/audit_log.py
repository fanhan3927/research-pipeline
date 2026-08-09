"""共享的项目操作日志工具。

对应 PRD 第八节「可追溯与可复现设计」：每个项目目录下维护一份
audit_log.md，记录每一步动作、人工确认内容、外部等待的起止时间。

用法（命令行）：
    python scripts/audit_log.py append <project_dir> \\
        --actor user|orchestrator \\
        --step "步骤名称" \\
        --detail "具体内容" \\
        [--pause-type confirm|external_wait]

也可以作为模块被其他脚本 import：
    from audit_log import append_entry
    append_entry(project_dir, actor="orchestrator", step="...", detail="...")
"""
from __future__ import annotations

import argparse
import datetime
from pathlib import Path

LOG_FILENAME = "audit_log.md"

HEADER = """# 项目操作日志

自动生成，记录本项目从原始材料到最终交付物的每一步操作。
每一行对应 PRD 6.5 节定义的两类暂停之一，或一次自动执行的步骤。

| 时间 | 执行方 | 步骤 | 暂停类型 | 详情 |
|---|---|---|---|---|
"""


def _log_path(project_dir: Path) -> Path:
    return project_dir / LOG_FILENAME


def ensure_log(project_dir: Path) -> Path:
    """确保 audit_log.md 存在，不存在则写入表头，返回文件路径。"""
    project_dir.mkdir(parents=True, exist_ok=True)
    path = _log_path(project_dir)
    if not path.exists():
        path.write_text(HEADER, encoding="utf-8")
    return path


def append_entry(
    project_dir: Path | str,
    actor: str,
    step: str,
    detail: str,
    pause_type: str = "-",
) -> None:
    """向指定项目的 audit_log.md 追加一条记录。

    actor: "user"（用户本人）或 "orchestrator"（编排层自动执行）
    pause_type: "confirm"（人工确认）/ "external_wait"（外部等待）/ "-"（不涉及暂停，自动步骤）
    """
    project_dir = Path(project_dir)
    path = ensure_log(project_dir)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 表格单元格里不能有裸的换行和竖线，做基本转义
    safe_detail = detail.replace("|", "\\|").replace("\n", "<br>")
    safe_step = step.replace("|", "\\|")
    line = f"| {timestamp} | {actor} | {safe_step} | {pause_type} | {safe_detail} |\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)


def _main() -> None:
    parser = argparse.ArgumentParser(description="项目操作日志工具")
    sub = parser.add_subparsers(dest="command", required=True)

    append_cmd = sub.add_parser("append", help="追加一条日志记录")
    append_cmd.add_argument("project_dir", type=Path, help="项目目录路径，如 projects/xxx_20260809")
    append_cmd.add_argument("--actor", required=True, choices=["user", "orchestrator"])
    append_cmd.add_argument("--step", required=True)
    append_cmd.add_argument("--detail", required=True)
    append_cmd.add_argument(
        "--pause-type",
        default="-",
        choices=["confirm", "external_wait", "-"],
    )

    args = parser.parse_args()
    if args.command == "append":
        append_entry(
            args.project_dir,
            actor=args.actor,
            step=args.step,
            detail=args.detail,
            pause_type=args.pause_type,
        )
        print(f"已记录到 {_log_path(args.project_dir)}")


if __name__ == "__main__":
    _main()
