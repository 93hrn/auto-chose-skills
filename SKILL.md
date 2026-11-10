---
name: auto-chose-skill
description: Use when a request needs real work (code, files, research, docs, data, architecture) — pick the right installed skill/plugin and call it directly, silently. Not for chat or one-line facts.
---

# auto-chose-skill

本技能把"先想用哪个技能、再问用户要不要用"压缩成一次判断 + 一次加载 + 直接干。

## 机制边界（先认清楚，别自欺）

- Hermes 的**技能只是系统提示里的索引条目**，没有"任务前回调"。本技能**不是**强制拦截层；它靠两件事生效：
  1. 插件 `auto-chose-skill` 的 `pre_llm_call` hook 每轮注入一句短指令（唯一能每次生效的机制）；
  2. 我在判断任务时按下面的流程走。
- 所以：**能做到"每轮被提醒"；做不到"框架级强制路由"**。任何自称做到了全局强制的说法都是假的。

## 一、是不是"任务"

要先过闸：**需要调用工具/多步/产出文件**的才算。

| 算 | 不算（直接答，别启动流程） |
|---|---|
| 写/改代码、跑命令、查仓库、排错 | 闲聊、打招呼 |
| 研究/检索并汇总结论 | 一句话事实问答 |
| 写文档、做表、做图、处理数据 | 纯翻译一段文本（不用工具时） |
| 设计、架构、评审、迁移 | 复述/润色我刚说过的话 |

判不准时按"算"处理 —— 多走一次清单只要 0.1 秒，漏掉一个技能可能毁掉整个任务。

## 二、四步循环

### 1. 判型（一行，不写给用户看）

在心里给任务贴一个类型：`排错 / 实现 / 设计 / 研究 / 文档 / 数据 / 图 / 演示 / 运维 / 安全 / 写作`。
再标两个属性：**要写文件吗**、**要不要多阶段**。这一步只产出这一行，不做推演。

### 2. 清单（唯一一次检索）

```bash
python "<本技能目录>/scripts/inventory.py"            # 全部已装技能 + 插件技能，实测 0.11 s
python "<本技能目录>/scripts/inventory.py" --grep ppt   # 用类型词过滤
```

- **只跑一次**。不要 `ls`、不要 `find`、不要重复调。
- `--grep` 支持多词 OR，用 `|` 分隔，**中英混着写最省事**：`--grep "ppt|幻灯片|演示"`、`--grep "debug|排错"`、`--grep "figure|图表|画图"`。
  词根参考：`debug` / `test` / `figure` / `ppt` / `write` / `research` / `spec` / `deliverable`。
  但 grep 只是**缩小范围**，别拿它当结论 —— 子串匹配很粗（搜 `search` 会命中"备忘录里搜索"）。
- 名字 + 一句话描述就够了；**不要为了比较而逐个读 SKILL.md**。
- **硬性排除**（连读都不用读）：
  - 带平台标记的（`[!macos]` / `[!linux,macos]`）—— 本机 Windows 跑不了；
  - 带 `[manual]` 的 —— 原作者声明只手动调，除非用户点名；
  - `auto-chose-skill` 自己 —— 不要自我递归。

### 3. 只读最接近的那 1 个（必要时 2 个）

- 用 `skill_view(<name>)` 读全文，或 `read_file` 读它的 SKILL.md。
- **读之前先确认职责对得上**：看描述里的"用于/不用于"两句，别只看关键词。
- 最多 2 个。第 2 个只在"第 1 个明确排除本任务"或"两者是先后阶段"时读。

### 4. 直接执行

- 按被选中技能的自身规范做，**把用户原话和约束原样带进去**。
- 不问"要不要用 X"，不推荐技能，不输出候选列表。
- 组合多个技能时**按阶段顺序**执行，并在阶段之间传递产物（不是并行乱跑）。

## 三、组合与顺序

- **一个够用就只要一个**。相似技能并存时（如 `tdd` / `test-driven-development` / `investigate` / `diagnosing-bugs`），选职责最贴的那个，**不要都调**。
- 需要多阶段时，顺序来自任务本身（研究 → 设计 → 实现 → 验证 → 交付），不是来自技能数量。
- 有明确工作流技能（`light-leader`、`dynamic-workflow`、`ask-matt`）时，让它们编排，不要自己叠。

## 三之二、重叠取舍表（照表选，别临场纠结）

| 任务 | 首选 | 别选 / 何时才换 |
|---|---|---|
| 测试先行写功能 | `tdd` | `test-driven-development` 是同义替代，**二选一**；不要两个都读 |
| 难 bug 要根因 | `investigate`（铁律：先证根因） | `diagnosing-bugs`（诊断循环，适合间歇性/性能回退）、`systematic-debugging`（4 阶段，通用）。三选一 |
| 提交前审查自己的改动 | `requesting-code-review`（安全扫描+质量门禁） | `code-review` 是"审自某基点以来的 diff / PR"，偏评审别人的改动 |
| 做 PPT | `ppt-master`（要成品：美化/模板/旁白/视频） | `pptx-deck-authoring`（要原生可编辑/精简）、`powerpoint`（程序化读写 .pptx）、`editable-pptx-authoring`（单页可编辑）、`ppt-master-windows-export`（**只在导出报错时**） |
| 中文 Word 交付报告 | `chinese-deliverable-docs` | `docx` 是通用读写/套模板，不负责中文交付格式 |
| Excel | `xlsx`（.xlsx/CSV） | 旧格式才用 `legacy-xls-editing`（改/对比 .xls）、`legacy-xls-template-fill`（往 .xls 模板填行） |
| 调研一个主题 | `research`（一手资料→仓库 Markdown） | `literature-search`（科研文献库/引文）、`arxiv`（只检索论文）、`grounded-citations`（给已有文档补引用） |
| 交接会话 | `handoff`（写交接文档） | `claude-handoff`（交给后台 agent 立刻接手干活 |
| 大工程怎么推进 | `dynamic-workflow`（能说清怎么切） | `wayfinder`（还说不清，要决策地图）、`to-tickets`（方案已定，只拆工单） |
| 科研全流程 | `light-leader`（跨阶段编排） | 单阶段直接 `light-*` 对应技能，不要为了"完整"套总控 |

## 四、静默

- 不说"正在激活/正在扫描/匹配到 X"。
- 默认无痕；用户开了 `/auto-chose explain` 才在首行加一句 `→ <skill 或 native>`。
- 例外只有五种：缺必要信息、要授权、要业务选择、所有可行路径都失败、有不可忽略的安全风险。

## 五、失败与例外

| 情况 | 动作 |
|---|---|
| 清单里没有匹配 | 用原生能力做，**不搜第二轮**，不报告"没找到技能" |
| 选中但加载失败 | 判因（文件缺失/依赖/权限）；换**一个**最接近的替代；仍失败再说 |
| 技能要外部依赖（R、LaTeX、gh、Docker） | 先探一次（`--version`），缺了就按技能里的降级说明走 |
| 不可逆/高风险操作 | 照常要授权。**自动匹配 ≠ 自动授权** |

## 六、Token 纪律

1. 判型只做一次；不重复分析用户已经说清的需求。
2. 清单只跑一次；不重复扫目录、不重复读同一个 SKILL.md。
3. 只为**已选中**的技能付全文加载成本。
4. 够用就停，不为了"看起来周全"多读一个。
5. 但**不省**：权限检查、依赖探测、结果验证、安全检查。

## 七、路由原则

阶段识别、依赖顺序、别重复造流程 —— 见 `references/routing-principles.md`
（提炼自 `mattpocock/skills` 的 `ask-matt`；只借原则，不搬它的知识库，因为那份知识库只覆盖它自己那 15 个技能）。

## 八、已知限制

- 不能在框架层强制；只能每轮提醒 + 每次判断时遵守。
- 不能切 Ponytail 模式（进程级；要 ultra 只能 `/ponytail ultra` 或 `PONYTAIL_DEFAULT_MODE`）。
- 插件在**下一次重启 Hermes** 后才加载；本会话内只有技能可用。
- 路由质量取决于技能描述质量：描述写得含糊的技能容易误配。
