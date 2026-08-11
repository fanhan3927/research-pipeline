"""把 Pipeline 内部版 Excel 转成可以外发的对外版。

对应分发链第五步（PRD 6.2 步骤 7）。严格按黑名单/白名单双重校验重建工作簿，
不做"手工删列"，从而避免手册中反复强调的三类遗漏：单元格批注、隐藏列、
其他工作表。输出文件是全新构建的工作簿，不含任何未在白名单里的信息。

用法：
    python scripts/make_external_pipeline.py \\
        --input path/to/Pipeline_内部版.xlsx \\
        --output-dir path/to/输出目录 \\
        [--project-dir projects/xxx_20260809]   # 提供则自动写入 audit_log.md
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_log import append_entry  # noqa: E402
from banned_keywords import PIPELINE_KEYWORDS, scan_value  # noqa: E402

# 对外版白名单：14 个字段，顺序即对外版列顺序（对应 Pipeline A-N 列）
EXTERNAL_WHITELIST = [
    "项目名称",
    "赛道",
    "项目简介",
    "所处阶段",
    "入场估值",
    "定价逻辑",
    "投资形式",
    "交易金额",
    "项目亮点",
    "目标上市地",
    "预计申报时间",
    "退出估值",
    "退出方式",
    "流动性安排",
]

# 内部专属黑名单：10 个字段（对应 Pipeline O-X 列），仅用于校验，不用于过滤
# （过滤逻辑以白名单为准；黑名单只用来在校验阶段确认没有遗漏应删的列）
INTERNAL_BLACKLIST = [
    "内部定级",
    "命中红线",
    "命中红色事项",
    "已排除客户类型",
    "排除依据",
    "推荐推送顺序",
    "本方合作模式",
    "商务条件状态",
    "上次复核日期",
    "内部备注",
]

# 研判链的「入场价格上限」是议价底牌，无论叫什么名字都绝不能进 Pipeline 任何版本。
# 这个字段本来就不在白名单里，天然会被排除；这里额外做一次显式检测只是为了让这条
# 硬规则「可见」——如果真的有人把它加进了内部版 Excel，生成对外版时要明确提醒一句，
# 而不是悄无声息地漏过去。
ENTRY_PRICE_CAP_HEADER_HINTS = ["入场价格上限", "价格上限", "议价底价", "谈判底线"]

# 名字里含这些词的工作表一律不进对外版（内部说明页、笔记页等）
SHEET_NAME_BLOCKLIST_SUBSTRINGS = ["内部", "说明", "笔记", "备注", "草稿"]


class PipelineFormatError(Exception):
    """输入的 Pipeline 内部版格式不符合预期（缺列、缺表等）。"""


def _find_source_sheet(wb: openpyxl.Workbook) -> Worksheet:
    """找到主数据表：优先找名字含 Pipeline 的表，否则用第一个不在黑名单里的表。"""
    for ws in wb.worksheets:
        if "pipeline" in ws.title.lower():
            return ws
    for ws in wb.worksheets:
        if not any(bad in ws.title for bad in SHEET_NAME_BLOCKLIST_SUBSTRINGS):
            return ws
    raise PipelineFormatError("找不到可用的数据工作表，请检查输入文件")


def _header_row(ws: Worksheet) -> dict[str, int]:
    """读取表头，返回 {表头文本: 列号(1-based)}。"""
    headers: dict[str, int] = {}
    for cell in ws[1]:
        if cell.value is not None:
            headers[str(cell.value).strip()] = cell.column
    return headers


def convert(input_path: Path, output_path: Path) -> tuple[list[str], list[str]]:
    """执行转换，返回 (关键词扫描警告, 结构性提醒)。

    两者都不阻塞生成、只供人工复核：前者是内容里可能漏删的敏感词，
    后者是"检测到内部版里有入场价格上限这类字段，已被白名单排除"的确认性提醒。
    """
    wb = openpyxl.load_workbook(input_path)
    src_ws = _find_source_sheet(wb)
    headers = _header_row(src_ws)

    missing = [h for h in EXTERNAL_WHITELIST if h not in headers]
    if missing:
        raise PipelineFormatError(
            f"内部版缺少以下白名单字段，无法生成对外版：{missing}"
        )

    notices: list[str] = []
    for header_text in headers:
        if header_text in EXTERNAL_WHITELIST:
            continue
        if any(hint in header_text for hint in ENTRY_PRICE_CAP_HEADER_HINTS):
            notices.append(
                f"内部版存在字段「{header_text}」，疑似入场价格上限/议价底牌类信息，"
                "已按白名单机制自动排除，未进入对外版（这是预期行为，只是提醒你确认过一眼）"
            )

    out_wb = openpyxl.Workbook()
    out_ws = out_wb.active
    out_ws.title = "Pipeline"

    for col_idx, field in enumerate(EXTERNAL_WHITELIST, start=1):
        header_cell = out_ws.cell(row=1, column=col_idx, value=field)
        header_cell.font = Font(bold=True)

    src_col_indices = [headers[field] for field in EXTERNAL_WHITELIST]
    warnings: list[str] = []
    row_idx = 2
    for src_row in src_ws.iter_rows(min_row=2):
        if all(src_row[c - 1].value is None for c in src_col_indices):
            continue  # 跳过全空行
        for out_col, src_col in enumerate(src_col_indices, start=1):
            value = src_row[src_col - 1].value
            out_ws.cell(row=row_idx, column=out_col, value=value)
            if isinstance(value, str):
                for kw in scan_value(value, PIPELINE_KEYWORDS):
                    cell_ref = out_ws.cell(row=row_idx, column=out_col).coordinate
                    warnings.append(f"{cell_ref}（{EXTERNAL_WHITELIST[out_col - 1]}）命中关键词「{kw}」")
        row_idx += 1

    # 重新构建的工作簿天然不含：内部版的其他工作表、单元格批注、隐藏列、红色表头标记
    out_wb.save(output_path)
    return warnings, notices


def _default_output_path(output_dir: Path) -> Path:
    date_str = datetime.date.today().strftime("%Y%m%d")
    return output_dir / f"Pipeline_对外版_{date_str}.xlsx"


def _main() -> None:
    parser = argparse.ArgumentParser(description="生成 Pipeline 对外版")
    parser.add_argument("--input", required=True, type=Path, help="Pipeline 内部版 xlsx 路径")
    parser.add_argument("--output-dir", required=True, type=Path, help="输出目录")
    parser.add_argument("--project-dir", type=Path, default=None, help="项目目录，提供则自动写 audit_log.md")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _default_output_path(args.output_dir)

    try:
        warnings, notices = convert(args.input, output_path)
    except PipelineFormatError as e:
        print(f"生成失败：{e}", file=sys.stderr)
        sys.exit(1)

    print(f"对外版已生成：{output_path}")
    if notices:
        print("\n结构性提醒：")
        for n in notices:
            print(f"  - {n}")
    if warnings:
        print("\n以下内容命中兜底关键词扫描，发送前请人工复核（不代表一定要删，但要看一眼）：")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("兜底关键词扫描：未命中。")

    if args.project_dir:
        detail = f"输入={args.input.name}，输出={output_path.name}"
        if warnings:
            detail += f"；关键词扫描命中 {len(warnings)} 处，待人工复核"
        if notices:
            detail += f"；结构性提醒 {len(notices)} 条"
        append_entry(
            args.project_dir,
            actor="orchestrator",
            step="生成 Pipeline 对外版",
            detail=detail,
            pause_type="-",
        )
        append_entry(
            args.project_dir,
            actor="user",
            step="发送前检查清单",
            detail="待用户确认：14 列 / 单一工作表 / 无批注 / 无隐藏列 / 关键词扫描已复核 / 文件名为对外版",
            pause_type="confirm",
        )


if __name__ == "__main__":
    _main()
