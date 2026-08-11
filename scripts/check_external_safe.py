"""对没有"内部版/对外版"区分、只出一份对外材料的文档（Teaser、Infographics 提示词、
Term Sheet），做发送前的关键词兜底扫描。

Pipeline 和研究报告都有内部版打底、对外版靠脚本机械清洗；投资人材料包（Teaser、
Infographics 提示词、Term Sheet）设计上只起草对外版一份，起草时不接触内部专属文件
本身就是主要的隔离机制（见 orchestrator/investor-package/SKILL.md）。这个脚本是
唯一的机械兜底——不做任何删改，只报告命中了什么，让人决定要不要改。

Term Sheet 是这三者里唯一需要读取 05_screening/04_forensics 部分内容（谈判清单、
必答项缺口）来生成条款的，转译时最容易带出怀疑性措辞或内部列名，所以用独立的
更宽的关键词表（--kind termsheet），不能跟 Teaser/Infographics 共用一份。

用法：
    python scripts/check_external_safe.py \\
        --input 08_investor_materials/Teaser_对外版_20260809.md \\
        [--kind teaser|infographics|termsheet]   # 默认 teaser（即原 INVESTOR_PACKAGE_KEYWORDS）
        [--project-dir projects/xxx_20260809]     # 提供则自动写 audit_log.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_log import append_entry  # noqa: E402
from banned_keywords import INVESTOR_PACKAGE_KEYWORDS, TERM_SHEET_KEYWORDS, scan_text  # noqa: E402

KEYWORD_SETS = {
    "teaser": INVESTOR_PACKAGE_KEYWORDS,
    "infographics": INVESTOR_PACKAGE_KEYWORDS,
    "termsheet": TERM_SHEET_KEYWORDS,
}


def _main() -> None:
    parser = argparse.ArgumentParser(description="对外材料发送前关键词兜底扫描")
    parser.add_argument("--input", required=True, type=Path, help="要检查的文件路径")
    parser.add_argument(
        "--kind", choices=sorted(KEYWORD_SETS), default="teaser",
        help="用哪份关键词表：teaser/infographics 用两条链对外禁用词并集，"
             "termsheet 用额外覆盖怀疑性措辞与 Pipeline 内部列名的更宽表",
    )
    parser.add_argument("--project-dir", type=Path, default=None, help="项目目录，提供则自动写 audit_log.md")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"文件不存在：{args.input}", file=sys.stderr)
        sys.exit(1)

    text = args.input.read_text(encoding="utf-8")
    hits = scan_text(text, KEYWORD_SETS[args.kind])

    if not hits:
        print(f"{args.input.name}：兜底关键词扫描未命中。")
    else:
        print(f"{args.input.name}：命中 {len(hits)} 处，发送前请人工复核（不代表一定要删，但要看一眼）：")
        for line_no, kw, line in hits:
            print(f"  - 第 {line_no} 行命中「{kw}」：{line[:60]}")

    if args.project_dir:
        detail = f"检查文件={args.input.name}（关键词表={args.kind}）"
        if hits:
            detail += f"；命中 {len(hits)} 处，待人工复核"
        append_entry(
            args.project_dir,
            actor="orchestrator",
            step="投资人材料包关键词兜底扫描",
            detail=detail,
        )
        confirm_detail = (
            "待用户确认：条款/数字均以对方能接受的口径转译，无怀疑性措辞、无内部定级、"
            "无我方基金自身的管理费/Carry 条款，关键词扫描已复核"
            if args.kind == "termsheet"
            else "待用户确认：内容仅取自两条链对外版文件，无内部专属信息，关键词扫描已复核"
        )
        append_entry(
            args.project_dir,
            actor="user",
            step=f"{args.input.name} 发送前检查",
            detail=confirm_detail,
            pause_type="confirm",
        )


if __name__ == "__main__":
    _main()
