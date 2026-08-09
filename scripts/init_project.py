"""按 PRD 5.1 的目录结构，为一个新项目建立归档骨架。

用法：
    python scripts/init_project.py --name "盛吉盛半导体" --chain distribution
    python scripts/init_project.py --name "某AI芯片项目" --chain rd
    python scripts/init_project.py --name "某项目" --chain both

生成 projects/<name>_<date>/ 及其子目录，并写入初始 audit_log.md。
项目目录默认不入库（见 .gitignore），本脚本只负责建骨架。
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_log import append_entry, ensure_log  # noqa: E402

PROJECTS_ROOT = Path(__file__).resolve().parent.parent / "projects"

# 子目录与所属链条的对应关系（见 PRD 5.1）
DISTRIBUTION_SUBDIRS = ["00_raw", "01_triage", "02_processing", "03_pipeline"]
RD_SUBDIRS = ["00_raw", "04_forensics", "05_screening", "06_valuation", "07_report"]

CHAIN_SUBDIRS = {
    "distribution": DISTRIBUTION_SUBDIRS,
    "rd": RD_SUBDIRS,
    "both": sorted(set(DISTRIBUTION_SUBDIRS) | set(RD_SUBDIRS)),
}

README_TEMPLATE = """# {name}

- 创建日期：{date}
- 启动链条：{chain}

## 目录说明

- `00_raw/`：原始项目材料，不做任何修改
- `01_triage/`：分发链研判结论（triage-matching 输出）
- `02_processing/`：分发链加工层产物（剥离+改写后的内容）
- `03_pipeline/`：Pipeline 内部版 / 对外版 Excel
- `04_forensics/`：研发链材料证伪产出
- `05_screening/`：研发链定性研判报告
- `06_valuation/`：研发链估值报告
- `07_report/`：研发链最终 PDF / PPT 大纲（内部版 + 对外版）

（未启动的链条对应目录会保留为空，不影响使用。）

## 追溯记录

本项目的完整操作轨迹见同级目录下的 `audit_log.md`。
"""


def slugify_date(date: datetime.date | None = None) -> str:
    return (date or datetime.date.today()).strftime("%Y%m%d")


def init_project(name: str, chain: str, date: datetime.date | None = None) -> Path:
    if chain not in CHAIN_SUBDIRS:
        raise ValueError(f"未知链条类型：{chain}，可选 distribution / rd / both")

    project_dir = PROJECTS_ROOT / f"{name}_{slugify_date(date)}"
    if project_dir.exists():
        raise FileExistsError(f"项目目录已存在：{project_dir}，如需重跑请直接在该目录下继续，不要重复初始化")

    for sub in CHAIN_SUBDIRS[chain]:
        (project_dir / sub).mkdir(parents=True, exist_ok=True)

    (project_dir / "README.md").write_text(
        README_TEMPLATE.format(name=name, date=slugify_date(date), chain=chain),
        encoding="utf-8",
    )

    ensure_log(project_dir)
    append_entry(
        project_dir,
        actor="orchestrator",
        step="项目初始化",
        detail=f"创建项目骨架，链条类型={chain}",
    )

    return project_dir


def _main() -> None:
    parser = argparse.ArgumentParser(description="初始化项目归档骨架")
    parser.add_argument("--name", required=True, help="项目名称，用于目录命名")
    parser.add_argument(
        "--chain",
        required=True,
        choices=["distribution", "rd", "both"],
        help="启动哪条链：distribution / rd / both",
    )
    args = parser.parse_args()

    project_dir = init_project(args.name, args.chain)
    print(f"项目骨架已创建：{project_dir}")


if __name__ == "__main__":
    _main()
