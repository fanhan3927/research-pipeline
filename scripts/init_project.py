"""按 PRD 5.1 的目录结构，为一个新项目建立归档骨架；如果项目已存在，
则补齐新链条需要的子目录（对应 PRD 6.4 两链自动衔接：分发链项目定级 A/B 后
启动研发链，不应该要求用户重新建一个项目、重新上传材料）。

用法：
    python scripts/init_project.py --name "盛吉盛半导体" --chain distribution
    python scripts/init_project.py --name "盛吉盛半导体" --chain rd   # 同名项目已存在则自动扩展
    python scripts/init_project.py --name "某项目" --chain both

生成/扩展 projects/<name>_<date>/ 及其子目录，并在 audit_log.md 里留痕。
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
- 已启动链条：{chain}

## 目录说明

- `00_raw/`：原始项目材料，不做任何修改
- `01_triage/`：分发链研判结论（triage-matching 输出）
- `02_processing/`：分发链加工层产物（剥离+改写后的内容）
- `03_pipeline/`：Pipeline 内部版 / 对外版 Excel
- `04_forensics/`：研发链材料证伪产出
- `05_screening/`：研发链定性研判报告
- `06_valuation/`：研发链估值报告
- `07_report/`：研发链最终 PDF / PPT 大纲（内部版 + 对外版）

（未启动的链条对应目录会保留为空，不影响使用。若后续从分发链切到研发链或反过来，
再次运行 `init_project.py` 会在原目录基础上补齐缺的子目录，不会新建一个重复项目。）

## 追溯记录

本项目的完整操作轨迹见同级目录下的 `audit_log.md`。
"""


class AmbiguousProjectError(Exception):
    """同名前缀匹配到多个项目目录，需要用户明确指定。"""


def slugify_date(date: datetime.date | None = None) -> str:
    return (date or datetime.date.today()).strftime("%Y%m%d")


def find_project_dir(name: str) -> Path | None:
    """按项目名找已存在的目录（忽略日期后缀），找不到返回 None。"""
    if not PROJECTS_ROOT.exists():
        return None
    matches = sorted(p for p in PROJECTS_ROOT.glob(f"{name}_*") if p.is_dir())
    if len(matches) > 1:
        names = "、".join(p.name for p in matches)
        raise AmbiguousProjectError(
            f"项目名「{name}」匹配到多个目录：{names}，请用完整目录名区分，不要用同名新建"
        )
    return matches[0] if matches else None


def _write_readme_if_missing(project_dir: Path, name: str, chain_desc: str, date_str: str) -> None:
    readme = project_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            README_TEMPLATE.format(name=name, date=date_str, chain=chain_desc),
            encoding="utf-8",
        )


def init_or_extend(name: str, chain: str, date: datetime.date | None = None) -> tuple[Path, bool, list[str]]:
    """建新项目，或在已有同名项目上补齐子目录。

    返回 (项目目录, 是否新建, 本次新增的子目录列表)。
    """
    if chain not in CHAIN_SUBDIRS:
        raise ValueError(f"未知链条类型：{chain}，可选 distribution / rd / both")

    existing = find_project_dir(name)
    created_new = existing is None
    project_dir = existing or (PROJECTS_ROOT / f"{name}_{slugify_date(date)}")

    added: list[str] = []
    for sub in CHAIN_SUBDIRS[chain]:
        sub_path = project_dir / sub
        if not sub_path.exists():
            sub_path.mkdir(parents=True)
            added.append(sub)

    _write_readme_if_missing(project_dir, name, chain, slugify_date(date))
    ensure_log(project_dir)

    if created_new:
        append_entry(
            project_dir,
            actor="orchestrator",
            step="项目初始化",
            detail=f"创建项目骨架，链条类型={chain}",
        )
    else:
        detail = f"新增子目录={added}" if added else f"链条={chain} 所需目录已存在，无需新增"
        append_entry(
            project_dir,
            actor="orchestrator",
            step="项目骨架扩展",
            detail=detail,
        )

    return project_dir, created_new, added


def _main() -> None:
    parser = argparse.ArgumentParser(description="初始化或扩展项目归档骨架")
    parser.add_argument("--name", required=True, help="项目名称，用于目录命名/查找")
    parser.add_argument(
        "--chain",
        required=True,
        choices=["distribution", "rd", "both"],
        help="启动哪条链：distribution / rd / both",
    )
    args = parser.parse_args()

    try:
        project_dir, created_new, added = init_or_extend(args.name, args.chain)
    except AmbiguousProjectError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)

    if created_new:
        print(f"项目骨架已创建：{project_dir}")
    elif added:
        print(f"已在现有项目上补齐子目录 {added}：{project_dir}")
    else:
        print(f"项目已存在且目录齐全，无需改动：{project_dir}")


if __name__ == "__main__":
    _main()
