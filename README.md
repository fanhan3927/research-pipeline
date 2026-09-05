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

3. **最终产出**（五个，前三个各自挂在一条链上，后两个要两条链都跑完才触发）
   - **分发链**：结构化 Pipeline Excel（内部版+对外版）
   - **研发链**：约 12 页 PDF 研究报告 + 15 页 PPT Deck 大纲 Markdown（各自内部版+对外版）——
     内部按**阶段与规模自动分流**：成长期至 Pre-IPO 走 `pe-hardtech-screening`+
     `hardtech-preipo-valuation`；种子/天使/Pre-A 且估值 3 亿元以内走
     `sequoia-seed-tech-startup-investment-evaluator` 一站式研判+估值
   - **投资人材料包**（两链都跑完后触发，只出对外版）：Teaser（Markdown）+ Infographics 提示词（JSON，供 ChatGPT 图片生成模型使用）

## 当前阶段

PRD 已确认（见 `docs/PRD.md`），Phase 1-7 已完成：分发链、研发链骨架，真实材料端到端验证（发现并修复 5 个真实问题），投资人材料包（已用真实案例验证），研发链早期项目分流路径。

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
│   ├── rd-chain/
│   │   └── SKILL.md                  # 研发链编排指令
│   └── investor-package/
│       └── SKILL.md                  # 投资人材料包编排指令（两链都跑完后触发）
├── scripts/
│   ├── audit_log.py                  # 项目操作日志（可追溯性基础设施）
│   ├── init_project.py               # 项目归档骨架初始化/跨链扩展
│   ├── banned_keywords.py            # 三条支线共用的发送前兜底关键词表
│   ├── project_status.py             # 查看项目进度（目录完成情况+历史暂停记录）
│   ├── make_external_pipeline.py     # 分发链：Pipeline 内部版 → 对外版
│   ├── generate_report_versions.py   # 研发链：研究报告/PPT大纲 → 内部版+对外版
│   ├── backfill_exit_valuation.py    # 两链衔接：退出估值回填 Pipeline + 自动重生对外版
│   └── check_external_safe.py        # 投资人材料包：Teaser/Infographics 提示词发送前关键词兜底扫描
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

## 快速开始（投资人材料包，需两条链都跑完）

```bash
# 按 orchestrator/investor-package/SKILL.md 的步骤，在 Claude Code 对话中
# 只读两条链已生成的对外版文件，起草 Teaser 和 3 份 Infographics 提示词

# 起草完成后跑一遍关键词兜底扫描（这两个产出物没有内部版可对比清洗，这是唯一的机械兜底）
python scripts/check_external_safe.py \
  --input projects/示例项目_20260809/08_investor_materials/Teaser_对外版_20260809.md \
  --project-dir projects/示例项目_20260809
```

