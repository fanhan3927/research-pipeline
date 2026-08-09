# research-pipeline
Automated research pipeline: PRD → Distribution Excel / R&amp;D PDF+PPT

自动化研究流水线工具，支持**分发链**与**研发链**两种模式，从需求梳理到最终交付物一站式生成。

## 项目目标

减少人工整理、记录与格式转换的繁琐工作，降低出错概率。通过标准化流程，快速产出高质量交付物。

## 核心流程

1. **启动时选择模式**
   - 分发链（Distribution）
   - 研发链（R&D）

2. **输入基础材料**
   - 用户提供初始信息与素材
   - 程序在处理过程中可主动追问补充信息或落地材料

3. **最终产出**
   - **分发链**：一份结构化的 Pipeline Excel 表
   - **研发链**：
     - 一份约 12 页的 PDF 研究报告
     - 一份 15 页的 PPT Deck 大纲（Markdown 格式）

## 当前阶段

PRD 已确认（见 `docs/PRD.md`），Phase 1（分发链）、Phase 2（研发链）、Phase 3（两链衔接细节）骨架已搭建。

## 依赖

```
pip install -r requirements.txt
```

## 目录结构

```
research-pipeline/
├── docs/
│   └── PRD.md                        # 产品需求文档
├── orchestrator/
│   ├── distribution-chain/
│   │   └── SKILL.md                  # 分发链编排指令
│   └── rd-chain/
│       └── SKILL.md                  # 研发链编排指令
├── scripts/
│   ├── audit_log.py                  # 项目操作日志（可追溯性基础设施）
│   ├── init_project.py               # 项目归档骨架初始化/跨链扩展
│   ├── banned_keywords.py            # 两条链共用的发送前兜底关键词表
│   ├── project_status.py             # 查看项目进度（目录完成情况+历史暂停记录）
│   ├── make_external_pipeline.py     # 分发链：Pipeline 内部版 → 对外版
│   ├── generate_report_versions.py   # 研发链：研究报告/PPT大纲 → 内部版+对外版
│   └── backfill_exit_valuation.py    # 两链衔接：退出估值回填 Pipeline + 自动重生对外版
├── projects/                         # 各项目的归档目录（默认不入库，见 .gitignore）
└── requirements.txt
```

## 快速开始（分发链）

```bash
# 1. 建项目骨架
python scripts/init_project.py --name "示例项目" --chain distribution

# 2. 按 orchestrator/distribution-chain/SKILL.md 的步骤，在 Claude Code 对话中
#    走完研判 → 商务条件确认 → 加工 → 入库 → 生成对外版

# 3. 内部版转对外版（脚本单独可测试）
python scripts/make_external_pipeline.py \
  --input projects/示例项目_20260809/03_pipeline/Pipeline_内部版.xlsx \
  --output-dir projects/示例项目_20260809/03_pipeline \
  --project-dir projects/示例项目_20260809
```

## 快速开始（研发链）

```bash
# 1. 建/扩展项目骨架（同名项目已存在时会在原目录上补齐子目录，不新建）
python scripts/init_project.py --name "示例项目" --chain rd

# 2. 按 orchestrator/rd-chain/SKILL.md 的步骤，在 Claude Code 对话中走完
#    材料证伪 → 定性研判 → 估值定价 → 整合起草内部版草稿（用 <!-- external:exclude --> 标记内部专属内容）

# 3. 内部版草稿转内部版+对外版 Markdown（脚本单独可测试）
python scripts/generate_report_versions.py \
  --input projects/示例项目_20260809/07_report/研究报告_内部版草稿.md \
  --output-dir projects/示例项目_20260809/07_report \
  --kind report \
  --project-dir projects/示例项目_20260809

# 4. 算完退出估值后，回填进该项目的 Pipeline（如果之前走过分发链）
python scripts/backfill_exit_valuation.py \
  --pipeline projects/示例项目_20260809/03_pipeline/Pipeline_内部版.xlsx \
  --project-name "示例项目" \
  --exit-valuation "80-95亿元（2027年科创板，按可比公司PS均值测算）" \
  --project-dir projects/示例项目_20260809
```

## 查看项目进度

```bash
python scripts/project_status.py --project-dir projects/示例项目_20260809
```

