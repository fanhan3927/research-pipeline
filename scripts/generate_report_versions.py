"""把研发链的研究报告 / PPT 大纲内部草稿，转成内部版 + 对外脱敏版两份 Markdown。

对应 PRD 第五节「报告生成层」与第七节「研发链对外版脱敏规则」。

设计原则和 make_external_pipeline.py 一致：**判断哪些内容属于内部专属，
是编排层/人在起草内部版草稿时就要做的事；本脚本只做机械的、可复核的转换**，
不重新读原始材料去猜。具体机制：

    起草内部版 Markdown 草稿时，把入场价格上限、IRR 反推过程、A/B/C 定级、
    go/no-go 结论、疑点三段式里的「冲突所在」分析、M1-M4 可信度分级标注等
    内部专属内容，包在这样的标记之间：

        <!-- external:exclude -->
        ...内部专属内容...
        <!-- /external:exclude -->

    本脚本生成对外版时，把标记之间的内容整段删除；标记之外的内容原样保留。

这比按标题名字猜测要可靠——起草者（负责整合 forensics/screening/valuation
产出的 Claude 编排指令，见 orchestrator/rd-chain/SKILL.md）明确知道自己写的
是内部专属内容还是可外发内容，用标记表达这个判断，脚本负责机械执行，
不需要脚本自己去理解语义。

用法：
    python scripts/generate_report_versions.py \\
        --input <内部版草稿.md> \\
        --output-dir <project_dir>/07_report \\
        --kind report|deck \\
        [--project-dir <project_dir>]
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_log import append_entry  # noqa: E402
from banned_keywords import REPORT_KEYWORDS, scan_text  # noqa: E402

EXCLUDE_BLOCK_RE = re.compile(
    r"<!--\s*external:exclude\s*-->.*?<!--\s*/external:exclude\s*-->\n?",
    re.DOTALL,
)

KIND_LABELS = {"report": "研究报告", "deck": "PPT大纲"}


class UnbalancedExcludeMarkerError(Exception):
    pass


def _check_balanced_markers(text: str) -> None:
    opens = len(re.findall(r"<!--\s*external:exclude\s*-->", text))
    closes = len(re.findall(r"<!--\s*/external:exclude\s*-->", text))
    if opens != closes:
        raise UnbalancedExcludeMarkerError(
            f"external:exclude 标记未配对：开始标记 {opens} 个，结束标记 {closes} 个，"
            "请检查内部版草稿"
        )


def sanitize_markdown(text: str) -> tuple[str, list[str]]:
    """返回 (对外版文本, 兜底关键词扫描警告列表)。"""
    _check_balanced_markers(text)
    external_text = EXCLUDE_BLOCK_RE.sub("", text)

    warnings = [
        f"第 {line_no} 行命中关键词「{kw}」：{line[:60]}"
        for line_no, kw, line in scan_text(external_text, REPORT_KEYWORDS)
    ]
    return external_text, warnings


def _default_names(kind: str) -> tuple[str, str]:
    date_str = datetime.date.today().strftime("%Y%m%d")
    label = KIND_LABELS[kind]
    return f"{label}_内部版_{date_str}.md", f"{label}_对外版_{date_str}.md"


def convert(input_path: Path, output_dir: Path, kind: str) -> tuple[Path, Path, list[str]]:
    text = input_path.read_text(encoding="utf-8")
    external_text, warnings = sanitize_markdown(text)

    output_dir.mkdir(parents=True, exist_ok=True)
    internal_name, external_name = _default_names(kind)
    internal_path = output_dir / internal_name
    external_path = output_dir / external_name

    internal_path.write_text(text, encoding="utf-8")
    external_path.write_text(external_text, encoding="utf-8")

    return internal_path, external_path, warnings


def _main() -> None:
    parser = argparse.ArgumentParser(description="生成研发链报告/大纲的内部版与对外版")
    parser.add_argument("--input", required=True, type=Path, help="内部版草稿 Markdown 路径")
    parser.add_argument("--output-dir", required=True, type=Path, help="输出目录（一般是 07_report/）")
    parser.add_argument("--kind", required=True, choices=list(KIND_LABELS), help="report=研究报告 / deck=PPT大纲")
    parser.add_argument("--project-dir", type=Path, default=None, help="项目目录，提供则自动写 audit_log.md")
    args = parser.parse_args()

    try:
        internal_path, external_path, warnings = convert(args.input, args.output_dir, args.kind)
    except (UnbalancedExcludeMarkerError, FileNotFoundError) as e:
        print(f"生成失败：{e}", file=sys.stderr)
        sys.exit(1)

    label = KIND_LABELS[args.kind]
    print(f"{label}内部版：{internal_path}")
    print(f"{label}对外版：{external_path}")
    if warnings:
        print(f"\n对外版命中兜底关键词扫描 {len(warnings)} 处，发送前请人工复核：")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("兜底关键词扫描：未命中。")

    if args.project_dir:
        detail = f"kind={args.kind}，输入={args.input.name}"
        if warnings:
            detail += f"；关键词扫描命中 {len(warnings)} 处，待人工复核"
        append_entry(
            args.project_dir,
            actor="orchestrator",
            step=f"生成{label}内部版/对外版",
            detail=detail,
        )
        append_entry(
            args.project_dir,
            actor="user",
            step=f"{label}对外版发送前检查",
            detail="待用户确认：无入场价格上限/IRR反推/内部定级/可信度分级标注，关键词扫描已复核",
            pause_type="confirm",
        )


if __name__ == "__main__":
    _main()
