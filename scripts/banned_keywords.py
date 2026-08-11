"""跨脚本共享的发送前兜底关键词扫描表。

两条链各自的对外版脚本（`make_external_pipeline.py`、`generate_report_versions.py`）
都需要做「关键词兜底扫描」这最后一道保险——万一起草/加工阶段该删的没删干净，
至少在生成对外版时再拦一次。这份表原本在两个脚本里各写了一份，容易改一处忘另一处
（比如新加一个禁用词，只加进了 Pipeline 那份），所以拆成共享模块。

两条链的关键词不完全一样（研发链多了 IRR/定级/可信度分级这些概念），
但重叠的部分（管理费、Carry、顾问费等）必须保持一致，这正是抽出来的原因。
"""
from __future__ import annotations

# 两条链共用的核心敏感词：商务条款、议价筹码相关
COMMON_KEYWORDS = [
    "管理费", "Carry", "顾问费", "撮合", "压价",
]

# 分发链对外版专属：Pipeline 手册「发送前的最后检查」里列出的两组词
PIPELINE_KEYWORDS = COMMON_KEYWORDS + [
    "急", "压力", "到期", "没卖出去",
]

# 研发链对外版专属：入场价格上限/定级/可信度分级等研判链铁律要求不外发的内容
REPORT_KEYWORDS = COMMON_KEYWORDS + [
    "入场价格上限", "IRR 反推", "目标IRR", "目标 IRR",
    "go/no-go", "Go/No-Go", "内部定级", "A/B/C 定级",
    "M1", "M2", "M3", "M4",
    "冲突所在",
]

# 投资人材料包（Teaser / Infographics 提示词）专属：两条链的对外禁用词并集。
# 这两个产出物只出对外版、没有内部版可对比清洗，关键词扫描是唯一的机械兜底，
# 所以宁可覆盖面宽一点，把两份列表都并进来。
INVESTOR_PACKAGE_KEYWORDS = sorted(set(PIPELINE_KEYWORDS) | set(REPORT_KEYWORDS))

# Term Sheet 专属：这份文件比 Teaser/Infographics 更特殊——起草时需要读
# 05_screening 的「谈判清单/红线条款」和 04_forensics 的「必答项缺口」来生成
# 交割先决条件与投资者保护条款，即读取范围本身就比纯营销材料更贴近内部文件，
# 转译时最容易带出两类东西：
#   1. preipo-material-forensics 手册里明令 L1 禁止的怀疑性措辞
#      （原文出自该 skill 的 output-templates.md「L1 件中禁止出现」清单）
#   2. hardtech-project-triage-matching Pipeline 内部版的十个专属列名
#      （原文出自 make_external_pipeline.py 的 INTERNAL_COLS）
# 这两类词单独看都不属于 INVESTOR_PACKAGE_KEYWORDS，因为 Teaser/Infographics
# 设计上根本不接触这两份内部文件，不会有这个风险；Term Sheet 会接触，所以要单列。
DOUBT_LANGUAGE_KEYWORDS = [
    "疑虚增", "存疑", "注水", "包装", "粉饰", "打问号", "对不上", "不实",
]
PIPELINE_INTERNAL_COLUMN_KEYWORDS = [
    "内部定级", "命中红线", "命中红色事项", "已排除客户类型", "排除依据",
    "推荐推送顺序", "本方合作模式", "商务条件状态", "上次复核日期", "内部备注",
]
# 我方专项基金自身的 LP-GP 经济条款（管理费/Carry/认购费等）已在 COMMON_KEYWORDS
# 里覆盖，但 Term Sheet 面向被投企业，这类条款出现在这里性质比出现在 Pipeline/
# Teaser 里更严重——那是我方与自己 LP 之间的条款，不是我方与被投企业之间的交易
# 条款，两者一旦在同一份文件里出现，等于把募资结构暴露给了被投企业。
TERM_SHEET_KEYWORDS = sorted(
    set(REPORT_KEYWORDS)
    | set(DOUBT_LANGUAGE_KEYWORDS)
    | set(PIPELINE_INTERNAL_COLUMN_KEYWORDS)
)


def scan_text(text: str, keywords: list[str]) -> list[tuple[int, str, str]]:
    """逐行扫描 text，返回 (行号, 命中关键词, 该行内容) 的列表。"""
    hits: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for kw in keywords:
            if kw in line:
                hits.append((line_no, kw, line.strip()))
    return hits


def scan_value(value: str, keywords: list[str]) -> list[str]:
    """扫描单个字符串（如 Excel 单元格值），返回命中的关键词列表。"""
    return [kw for kw in keywords if kw in value]
