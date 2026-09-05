---
name: rd-chain-orchestrator
description: >-
  研发链编排层。串联 preipo-material-forensics 与两条阶段分流路径——
  成长期至 Pre-IPO 路径（pe-hardtech-screening → hardtech-preipo-valuation）、
  种子/天使/Pre-A 且估值 3 亿元以内路径（sequoia-seed-tech-startup-investment-evaluator
  一站式完成研判+估值）——自动推进材料证伪、定性研判、估值定价，
  并整合产出为 12 页研究报告（PDF）+ 15 页 PPT 大纲（Markdown），
  各自产出内部完整版与对外脱敏版。当用户说"走研发链""这个项目要出研判报告"
  "帮我把这个项目做深度研判并出报告"时触发。
  本文件本身不做材料证伪/研判/估值判断，判断逻辑全部委托给它编排的 skill；
  它只负责：按顺序触发、在关键节点暂停提问、整合产出、调用脚本生成文件、写操作日志。
---

# 研发链编排层

对应 `docs/PRD.md` 第 6.3 / 6.4 / 6.5 / 5.2 / 七 节。本文件是给执行编排任务的 Claude 看的
操作手册，不是给最终用户看的产品文档。

## 前置动作：建/扩展项目骨架

```
python scripts/init_project.py --name "<项目名称>" --chain rd
```

如果这个项目名此前已经通过分发链建过（`--chain distribution`），上面这条命令会在
**同一个项目目录**里补齐 `04_forensics/05_screening/06_valuation/07_report/` 四个子目录，
不会新建一个重复项目——这正是 6.4 节"分发链定级 A/B 后自动询问是否启动研发链"要用到的
衔接机制。已有的 `00_raw/` 材料、`01_triage/` 研判结论可以直接复用，不要求用户重新上传。

## 步骤 1：材料证伪（默认快筛）

触发 `preipo-material-forensics`，把项目材料喂给它，产出落 `04_forensics/`。默认只跑快筛
（一页纸速读备忘），不要一上来就深读。

## 步骤 2（人工确认）：是否深读

快筛结果出来后，停下来问：

> 快筛结果如上（门禁警告 / 七问表 / 三个关键疑点）。要不要深读，出完整的问题清单？

- 疑点致命，用户选择不深读 → 提示"建议归档，暂不继续"，流程到此结束。
- 用户选择深读 → 继续步骤 3。

日志：
```
python scripts/audit_log.py append <project_dir> --actor user \
  --step "是否深读决定" --detail "<用户的选择及理由摘要>" --pause-type confirm
```

## 步骤 3：深读

在 `preipo-material-forensics` 同一对话里说"深读，出问题清单"，拿到三份文件：内部研判备忘、
外发《补充材料清单》（Word）、移交字段表。都落 `04_forensics/`。

**3.1（外部等待，可能阻塞后续）**：把《补充材料清单》发给项目方，提示用户"材料回来之前，
Step 4-6 需要的信息可能不全"。给用户两个选项：

- 等材料回来再继续（更稳）→ 暂停在这里
- 先按现有信息推进，缺项在报告里标注"待补充"（更快，但 screening/valuation 的判断质量会打折）

不管选哪个都要记下来，方便以后复现时知道当时是在什么信息基础上做的判断：

```
python scripts/audit_log.py append <project_dir> --actor orchestrator \
  --step "发出补充材料清单" --detail "等待项目方回复" --pause-type external_wait
python scripts/audit_log.py append <project_dir> --actor user \
  --step "是否等待材料回复" --detail "<用户选择：等待 / 先推进>" --pause-type confirm
```

材料回来后，用户重新上传，说"材料回来了，重新上传更新一下"，编排层只重跑受影响的部分
（一般是步骤 3 的更新 + 步骤 4 及之后），不用从步骤 1 整个重来。

**解除等待时，日志要用同一个 `--pause-type external_wait` 记录，不要用默认的 `-`**——
`project_status.py` 只筛出 `confirm`/`external_wait` 两类记录展示，如果解除记录不带这个标记，
在那份筛选视图里会一直显得"还在等"，即使实际已经继续往下跑了：

```
python scripts/audit_log.py append <project_dir> --actor user \
  --step "补充材料清单回复" --detail "<材料回来了的摘要，或注明是模拟/测试数据>" \
  --pause-type external_wait
```

（这条踩坑是 Phase 4 真实材料验证时发现的：忘记带这个标记，`project_status.py` 就会
误判流程还卡在等待材料这一步。）

## 步骤 3.5（人工确认，二选一路由）：阶段与规模分流

这一步决定步骤 4-6 走哪条路径，**不要凭感觉选，按明确规则判断**：

| 条件 | 路径 |
|---|---|
| 种子/天使/Pre-A 轮，**且**投后估值 ≤ 3 亿元人民币 | **B 路径**：`sequoia-seed-tech-startup-investment-evaluator` 一站式完成 |
| A 轮及以后，或估值 > 3 亿元，或已是成长期至 Pre-IPO | **A 路径**：原有 `pe-hardtech-screening` → `hardtech-preipo-valuation` |
| 轮次/估值材料里没写清楚，判断不了 | 停下来问用户，不要猜 |

**已知的一处口径差异，明确标注、不做隐藏处理**：`sequoia-seed-tech-startup-investment-evaluator`
skill 自身手册里声明的适用范围是"投后估值 2 亿元人民币以内"，比本编排层这条 ≤3 亿元的
路由阈值更窄。这是编排层刻意做出的更宽松判断（业务方要求放宽 B 路径覆盖面），不是遗漏或
不一致——2-3 亿元区间的项目会被本编排层路由进一个"自称"上限为 2 亿元的 skill。如果
该 skill 后续版本更新后在这个区间给出的判断质量明显不如预期（比如估值方法论对超过它
自身声明上限的项目适配变差），应该把这条差异重新提出来，考虑是否需要收紧回 2 亿元，
或者等 skill 自身更新其适用范围声明。

判断依据从步骤 3 的移交字段表里取（"本轮融资额（增资/老股）""本轮投前估值""所处阶段"
这几个字段），通常不需要额外问用户；只有字段缺失或边界不清（比如"Pre-A+"这种模糊说法、
或估值区间刚好跨在 3 亿元上下）时才需要人工确认：

> 这个项目属于早期轮次，但阶段/估值材料里不够明确——是按 3 亿元以内的早期项目评估法
> （红杉方法），还是按常规成长期研判+估值流程走？

日志：
```
python scripts/audit_log.py append <project_dir> --actor user \
  --step "阶段与规模分流判断" --detail "<A路径/B路径，判断依据>" --pause-type confirm
```

**这条分流是 Phase 7 新增的**——在此之前，早期项目只能硬套 `pe-hardtech-screening` 里
"天使/Pre-A"那档通用权重、然后直接跳过估值（因为 `hardtech-preipo-valuation` 明确是
Pre-IPO 前 12-24 个月专属，套不上早期项目）。这意味着早期项目此前压根拿不到任何入场
估值判断，只有定性研判。`sequoia-seed-tech-startup-investment-evaluator` 补上了这一块——
它是专门针对种子/天使/Pre-A、3 亿元以内标的设计的完整方法论（创始人七维打分 →
STRONG_YES/PROCEED_TO_VOTE/REJECT → "人事匹配估值法"给入场估值区间/持股比例/条款建议 →
10x 反向检验），走 B 路径的项目不再是"只研判不估值"，而是拿到一份完整的研判+估值结论。

### A 路径 — 步骤 4A：定性研判

触发 `pe-hardtech-screening`，输入是步骤 3 的移交字段表（不是原始材料——避免各 skill
各自重读原始材料、产出口径打架，这条规则在原手册里是硬性的，编排层要遵守）。产出七步研判报告，
落 `05_screening/`。自动执行，不暂停。

### A 路径 — 步骤 5A（人工确认）：可比公司倍数

`hardtech-preipo-valuation` 需要可比公司 PE/PS 倍数，这是硬约束，编排层不能替用户猜、
不能从材料里的同业数据自动代入。明确停下来问：

> 要算估值了，麻烦给几家可比公司的 PE/PS 倍数（公司名 + 倍数 + 取数时点），
> 我不会替你猜这个数字。

日志：
```
python scripts/audit_log.py append <project_dir> --actor user \
  --step "可比公司倍数输入" --detail "<用户提供的可比公司与倍数>" --pause-type confirm
```

### A 路径 — 步骤 6A：估值定价

触发 `hardtech-preipo-valuation`，用步骤 4A 的移交字段表 + 步骤 5A 用户提供的可比公司倍数。
拿到退出估值区间、入场价格上限、净资产安全垫验证、情景分析，落 `06_valuation/`。自动执行，
不暂停。

### B 路径 — 步骤 4B：早期项目一站式评估

触发 `sequoia-seed-tech-startup-investment-evaluator`，输入同样是步骤 3 的移交字段表
（不是原始材料，理由同上）；如果字段表里没有创始人履历/访谈纪要这类该 skill 需要的
细节，提示用户是否要补充材料，缺了也不阻塞——按该 skill 自己的规则处理数据不全的情况。

产出：创始人七维雷达评分（Education / Work Experience / Reference Check / IQ / EQ /
Vision / Outlier）、STRONG_YES / PROCEED_TO_VOTE / REJECT 结论、入场估值区间、持股比例、
条款建议、10x 反向检验。全部落 `05_screening/`（这条路径一站式完成了研判+估值两件事，
不再需要 `06_valuation/`，该目录本次留空即可，不是遗漏）。自动执行，不暂停。

**B 路径没有"可比公司倍数"这一步**——`sequoia-seed-tech-startup-investment-evaluator`
的估值方法论（人事匹配估值法）不依赖用户提供可比公司倍数，这是它和
`hardtech-preipo-valuation` 的方法论差异，不是编排层偷懒省掉了这一步。

## 步骤 7：整合，起草内部版草稿

这是编排层自己要做的整合动作，不是某个 skill 的输出。把步骤 1/3（证伪）、步骤 4A/4B
（研判，含估值）的产出，按下面的章节结构整合成一份 Markdown 草稿（12 页是软性篇幅目标，
按实际内容量增减，不硬凑）：

1. 项目概览
2. 材料可信度与核心疑点（保留可采信事实列表；疑点用三段式，但按下面的标记规则处理）
3. 团队与治理
4. 技术与护城河
5. 财务与数据质量
6. 退出路径与确定性
7. 估值与入场价格测算
8. A-B-C 结论与建议

**A 路径和 B 路径在第 6、7、8 章的内容来源不同**，起草时不要弄混：

| 章节 | A 路径（screening+valuation） | B 路径（sequoia） |
|---|---|---|
| 六、退出路径与确定性 | 来自 `hardtech-preipo-valuation` 的退出路径分析，通常有实质内容 | 项目阶段过早，通常没有明确退出路径判断——**如实精简或说明"阶段过早，退出路径暂不适用"，不要为了凑结构编内容** |
| 七、估值与入场价格测算 | 退出估值区间 + 入场价格上限 + IRR 反推过程 | 创始人七维雷达评分 + 入场估值区间 + 持股比例 + 条款建议 + 10x 反向检验 |
| 八、A-B-C 结论与建议 | go/no-go 结论 | STRONG_YES / PROCEED_TO_VOTE / REJECT 结论 |

**起草时必须遵守的标记规则**（`scripts/generate_report_versions.py` 依赖这个规则做机械转换，
自己不做语义判断）：任何只能内部看、不能外发的内容，包在这两行之间：

```
<!-- external:exclude -->
...内部专属内容...
<!-- /external:exclude -->
```

对照 PRD 第七节的表，下面这些必须包进标记里（两条路径通用）：
- 第 8 章整章：go/no-go 结论，或 STRONG_YES/PROCEED_TO_VOTE/REJECT 结论
- 第 7 章里的**入场类**数字：入场价格上限、目标 IRR 反推过程（A 路径）；入场估值区间、
  持股比例、条款建议、创始人七维评分明细（B 路径）——**这些都是我们的议价筹码或内部
  评估依据，性质和"入场价格上限"完全一样，不区分路径，一律不外发**
- 材料可信度分级标注（M1/M2/M3/M4）、疑点三段式里的"冲突所在"分析
  （"需项目方回答"部分如果要保留成问题清单，放在标记外面，或者干脆不放进报告正文，
  直接引用 `04_forensics/` 里已经外发过的《补充材料清单》）

这些不需要包起来，原样保留：
- **退出**估值区间、退出路径分析（判断标的价值，不是议价筹码）——注意 B 路径的
  "入场估值区间"跟这个是两回事，前者是我们打算出的价，后者是标的未来值多少，**千万
  不要把 B 路径的入场估值区间当成退出估值处理**，见下方"两链衔接"一节
- 团队/技术/护城河的客观描述（未经验证的表述要注明"未经独立核实"）

把草稿存成 `07_report/研究报告_内部版草稿.md`。

## 步骤 8：生成研究报告的内部版/对外版 Markdown

```
python scripts/generate_report_versions.py \
  --input <project_dir>/07_report/研究报告_内部版草稿.md \
  --output-dir <project_dir>/07_report \
  --kind report \
  --project-dir <project_dir>
```

脚本会机械地按标记删除内部专属内容，生成对外版，并做一遍关键词兜底扫描。

## 步骤 9：渲染 PDF

用 `pdf` skill，把步骤 8 产出的内部版 Markdown 渲染成内部版 PDF、对外版 Markdown 渲染成
对外版 PDF，都存进 `07_report/`。这一步是纯排版转换，不涉及判断，不暂停。

## 步骤 10：起草并生成 PPT 大纲

同样先起草一份 Markdown 大纲草稿（15 页软性目标，按 8 章内容重新组织成适合口头汇报的
大纲形式：每页一个要点+3-5 条支撑信息），用同样的 `<!-- external:exclude -->` 标记规则，
存成 `07_report/PPT大纲_内部版草稿.md`，然后跑：

```
python scripts/generate_report_versions.py \
  --input <project_dir>/07_report/PPT大纲_内部版草稿.md \
  --output-dir <project_dir>/07_report \
  --kind deck \
  --project-dir <project_dir>
```

**这一步只产出 Markdown，不调用 `pptx` skill、不生成 .pptx 文件**——用户会用自己的工具
把大纲做成正式 PPT。

## 步骤 11（人工确认）：对外版发送前检查

步骤 8 和步骤 10 各自触发了一条 `pause-type confirm` 的日志（脚本自动写的），但脚本的
关键词扫描不能替代人工判断。把结果念给用户，逐项确认：

> □ 报告对外版里没有入场价格上限、IRR 反推过程（A 路径）或入场估值区间/持股比例/条款
> 建议/创始人评分明细（B 路径）　□ 没有 go/no-go 或 STRONG_YES/PROCEED_TO_VOTE/REJECT 结论
> □ 没有 M1-M4 可信度分级标注　□ 没有疑点三段式里的"冲突所在"分析
> □ 关键词扫描结果已看过并确认无误　□ PPT 大纲对外版同样检查过一遍

用户明确确认后：
```
python scripts/audit_log.py append <project_dir> --actor user \
  --step "研发链对外版发送前检查确认" --detail "用户确认可以发送" --pause-type confirm
```

到这里，研发链完成。**内部版（PDF+Markdown）默认不外发**——即使检查通过，也只有明确标注
"对外版"的那一份可以往外发，这是研发链继承自原手册的铁律，编排层任何时候都不能建议用户
直接发内部版。

## 两链衔接（PRD 6.4，反向）

**这一步只适用于走了 A 路径的项目。** B 路径（sequoia）产出的是"入场估值区间"，跟 Pipeline
"退出估值"字段要求的"标的未来值多少"是两个方向相反的判断——入场估值区间是我们打算按
什么价格进，属于议价筹码，跟入场价格上限地位一样，**不能填进 Pipeline 的退出估值字段，
也不能填进 Pipeline 任何其他字段**。B 路径的项目，Pipeline 的"退出估值"字段就如实留空
（`pipeline-intake` 会标 missing，这是诚实的结果，不是缺陷——早期项目本来就很难判断
退出时值多少，不应该拿入场估值区间去凑一个假的"退出估值"）。

如果这个项目之前走过分发链、`03_pipeline/Pipeline_内部版.xlsx` 已经存在，且**走的是
A 路径**，步骤 6A 算出退出估值后就跑：

```
python scripts/backfill_exit_valuation.py \
  --pipeline <project_dir>/03_pipeline/Pipeline_内部版.xlsx \
  --project-name "<项目名称，须与 Pipeline 里完全一致>" \
  --exit-valuation "<退出估值区间+口径>" \
  --project-dir <project_dir>
```

这个脚本会自动：回填内部版的"退出估值"列、重新生成一份对外版、在 audit_log.md 里补一条
"发送前检查清单（退出估值更新后）"的人工确认记录——**提醒用户这份新生成的对外版也要重新走
一遍发送前检查，不能因为之前检查过旧版本就直接发新版本**。

如果该项目还没走过分发链、没有 `Pipeline_内部版.xlsx`，这一步跳过，等以后启动分发链时
`pipeline-intake` 会正常处理这个字段（缺了就标 missing，不用现在纠结）。

**入场价格上限（A 路径）、入场估值区间/持股比例/条款建议（B 路径）任何情况下都不允许
写入 Pipeline 的任何版本**——这条和分发链编排层的规则一致，两边都要遵守。
`backfill_exit_valuation.py` 从设计上就只能写"退出估值"这一个字段，没有提供写入其他
字段的参数，不要绕开这个脚本去手工把估值报告里的这些内部数字抄进 Pipeline。
