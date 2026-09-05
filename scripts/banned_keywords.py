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
# 含 A 路径（screening+valuation）与 B 路径（sequoia 早期项目一站式评估）两套内部判断用语——
# 两条路径产出不同，但都属于"入场类"议价筹码或内部评估依据，禁用规则一视同仁
REPORT_KEYWORDS = COMMON_KEYWORDS + [
    "入场价格上限", "IRR 反推", "目标IRR", "目标 IRR",
    "go/no-go", "Go/No-Go", "内部定级", "A/B/C 定级",
    "M1", "M2", "M3", "M4",
    "冲突所在",
    # B 路径（sequoia-seed-tech-startup-investment-evaluator）专属
    "入场估值区间", "STRONG_YES", "PROCEED_TO_VOTE", "REJECT",
    "人事匹配估值法", "七维雷达", "10x 反向检验", "10x反向检验",
]

# 投资人材料包（Teaser / Infographics 提示词）专属：两条链的对外禁用词并集。
# 这两个产出物只出对外版、没有内部版可对比清洗，关键词扫描是唯一的机械兜底，
# 所以宁可覆盖面宽一点，把两份列表都并进来。
INVESTOR_PACKAGE_KEYWORDS = sorted(set(PIPELINE_KEYWORDS) | set(REPORT_KEYWORDS))


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
