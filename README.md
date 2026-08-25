# LLM Wiki Framework

> 一套经过实战验证的 **LLM 驱动知识库管理框架**。用自然语言工作指引替代传统代码逻辑，让 Claude（或其他 LLM）按标准化流程摄入、检索和维护你的 Markdown 知识库。

**适用场景**: 机构知识管理、个人笔记体系化、政策研究、案例库建设。虽然脱胎于高校管理场景，但框架本身与领域无关。

---

## 设计哲学

三条原则贯穿始终：

| 原则 | 含义 |
|------|------|
| **标签是地基** | 所有知识页通过统一的标签体系组织，禁止 LLM 凭空捏造标签，确保检索一致性 |
| **进出有记录** | 每次知识入库必须更新 source 和 last-updated，形成可追溯的知识演化链 |
| **方法标准化** | 不同文件类型对应固定的提取方法论，LLM 只需按路由选择，不自行发挥 |

---

## 系统架构

```mermaid
flowchart TD
    subgraph User["👤 用户"]
        T1["说 '同步检测'"]
        T2["说 '学习新增'"]
        T3["说 '查/关于XXX'"]
        T4["说 '健康检查'"]
        T5["说 '对比分析'"]
        T6["说 '调整格式'"]
        T7["说 '框架同步'"]
        T8["说 '撰写评论/第一议题'"]
    end

    subgraph Control["🧠 控制层 (claude/)"]
        CLAUDE["CLAUDE.md<br/>总控工作指引"]
        SYNC["sync-log.py<br/>增量检测脚本"]
        POLICY["policy-organize.py<br/>制度梳理脚本"]
        DOCX["docx-formatter.py<br/>公文格式管道"]
        DOCXV["docx-validate.sh<br/>导出验证脚本"]
    end

    subgraph Agents["🤖 Agent 层 (claude/agents/)"]
        AG_DOCX["docx-formatter<br/>公文格式调整+修订"]
        AG_SYNC["framework-sync<br/>框架同步→GitHub"]
    end

    subgraph Schema["📐 规范层 (schema/)"]
        S0["0.index.md<br/>规则索引"]
        S1["1.frontmatter-spec.md<br/>元数据规范"]
        S2["2.tag-index-template.md<br/>标签字典"]
        S3["3.learning-methods.md<br/>学习方法论"]
        S4["4.domain-extension-example.md<br/>领域扩展模板"]
        S5["4.writing-guide.md<br/>写作总指引"]
        S6["4a/4b.pattern-*.md<br/>写作范式"]
        S7["5.persona-guide.md<br/>人物画像建模"]
        S8["6.lint-guide.md<br/>健康检查规范"]
    end

    subgraph Pipeline["⚙️ 工作流"]
        K_IN["Knowledge-IN<br/>6步摄入流水线"]
        K_OUT["Knowledge-OUT<br/>4步知识检索"]
        K_LINT["Knowledge-LINT<br/>五层健康检查 L0-L4"]
        K_CMP["对比模式<br/>C1-C6 修改痕迹建模"]
        K_WRITE["写作体系<br/>范式×画像组合"]
    end

    subgraph Data["📦 数据层"]
        RAW["raw/<br/>原始语料(不可变)"]
        WIKI["wiki/<br/>知识萃取"]
        WIKI_E["entities/ 实体页"]
        WIKI_C["concepts/ 概念页"]
        WIKI_S["synthesis/ 综合分析"]
    end

    T1 --> SYNC
    T2 --> K_IN
    T3 --> K_OUT
    T4 --> K_LINT
    T5 --> K_CMP
    T6 --> AG_DOCX
    T7 --> AG_SYNC
    T8 --> K_WRITE

    CLAUDE --> K_IN
    CLAUDE --> K_OUT
    CLAUDE --> K_LINT
    CLAUDE --> K_CMP
    CLAUDE --> K_WRITE
    CLAUDE --> AG_DOCX
    CLAUDE --> AG_SYNC

    K_IN --> K_CMP
    K_IN --> S2
    K_IN --> S3
    K_IN --> S1
    K_WRITE --> S5
    K_WRITE --> S6
    K_WRITE --> S7
    K_LINT --> S8
    AG_DOCX --> DOCXV

    SYNC --> RAW
    K_IN --> RAW
    K_IN --> WIKI
    K_OUT --> WIKI
    K_LINT --> WIKI
    K_CMP --> WIKI
    K_WRITE --> WIKI

    WIKI --> WIKI_E
    WIKI --> WIKI_C
    WIKI --> WIKI_S
```

### 架构分层

| 层 | 目录 | 职责 | 关键文件 |
|---|------|------|---------|
| **控制层** | `claude/` | 定义 LLM 行为的自然语言工作指引 + 工具脚本 | `CLAUDE.md`, `sync-log.py`, `policy-organize.py`, `docx-formatter.py`, `docx-validate.sh` |
| **Agent 层** | `claude/agents/` | 可复用的领域 Agent 定义，每个 Agent 封装完整工作流 | `docx-formatter.md`, `framework-sync.md` |
| **规范层** | `schema/` | 规则标准，不包含知识内容 | 10 个 .md 规范文件（含写作/画像/健康检查扩展） |
| **数据层** | `raw/` + `wiki/` | 原始语料（不可变）+ 知识萃取（可写）| 用户按需填充 |

核心思路：**控制层告诉 LLM 做什么，Agent 层封装怎么做，规范层约束标准，数据层是操作对象。**

---

## 目录结构

```
your-knowledge-base/
├── .claude/                ← Claude Code 配置（可选，如果你用 Claude Code）
├── claude/                 ← 本框架：工作流配置
│   ├── CLAUDE.md           ← LLM 总控工作指引
│   ├── sync-log.py         ← 增量检测 + 空壳扫描
│   ├── policy-organize.py  ← 制度文件分类与重命名
│   ├── docx-formatter.py   ← 公文格式管道脚本
│   ├── docx-validate.sh    ← docx 导出后验证脚本
│   └── agents/             ← Agent 定义
│       ├── docx-formatter.md  ← 公文格式调整 Agent
│       └── framework-sync.md  ← 框架同步 Agent
├── schema/                 ← 本框架：规则标准
│   ├── 0.index.md          ← 规则索引
│   ├── 1.frontmatter-spec.md ← Frontmatter 规范
│   ├── 2.tag-index-template.md ← 标签体系模板
│   ├── 3.learning-methods.md   ← 结构化学习法（含对比模式）
│   ├── 4.writing-guide.md      ← 写作总指引（范式×画像组合）
│   ├── 4a.pattern-first-agenda.md ← 第一议题表态范式
│   ├── 4b.pattern-people-forum.md ← 人民论坛评论范式
│   ├── 5.persona-guide.md      ← 人物画像建模标准
│   ├── 6.lint-guide.md         ← 健康检查规范（五层 L0-L4）
│   └── 4.domain-extension-example.md ← 领域扩展模板
├── templates/              ← 本框架：初始化模板
│   └── wiki-directory-structure.md
├── raw/                    ← 原始语料（只写不入）
│   ├── policy/             ← 政策文件
│   ├── sources/            ← 外部来源
│   ├── practice/           ← 实践材料
│   ├── documents/          ← 内部文档
│   ├── case-studies/       ← 案例
│   ├── research/           ← 研究资料
│   └── interviews/         ← 访谈
└── wiki/                   ← 知识萃取（可写可改）
    ├── index.md            ← 导航中心
    ├── log.md              ← 操作日志
    ├── open-questions.md   ← 待解决问题
    ├── entities/           ← 机构、人物实体页
    ├── concepts/           ← 概念、知识点页
    └── synthesis/          ← 综合分析产出
```

---

## 工作流详解

### 1. Knowledge-IN（知识摄入）

**触发词**: "学习"、"提炼"、"入库"

最核心的流程——将原始文件转化为结构化知识并写入 wiki。

```
Step 1: 文件诊断
   ├─ 运行 sync-log.py 发现新文件
   ├─ 判定文件状态：非md/链接壳/图片型/正常md
   └─ 每个文件必须有诊断标签

Step 2: 格式预处理（仅异常状态文件）
   ├─ .docx/.pdf → 转换为 .md
   ├─ 链接壳 → defuddle 提取网页正文
   └─ 图片型 → OCR 提取文字

Step 3: 讨论确认
   └─ AI 列出 3-5 条核心要点，用户确认方向

Step 4: 按类型提取
   ├─ 政策类 → 政策学习法（5步）
   ├─ 案例类 → 案例拆解法（四问+双写）
   ├─ 学术类 → 观点萃取法（3步）
   └─ 🔀 对比模式 → 六维对比 C1-C6（自动检测触发）

Step 5: 存储
   ├─ 外部来源 → wiki/concepts/ 或 wiki/entities/
   └─ 内部文件 → 三层分流（稳定层/年度层/事件层）

Step 6: 更新记录
   └─ frontmatter source置顶 + last-updated更新
```

### 2. Knowledge-OUT（知识调用）

**触发词**: "查"、"调取"、"关于XXX"

```
解析需求 → Grep检索wiki + schema → 输出结果(标来源+置信度) → 有价值则回写synthesis/
```

### 3. Knowledge-LINT（健康检查）`五层体系 in v6.3`

**触发词**: "健康检查"、"查矛盾"、"查遗漏"

健康检查从"内容体检"升级为**五层体系（L0-L4）**，完整规范见 `schema/6.lint-guide.md`：
- **快检**（默认）：L0 内容层 + L1 工作流资产层（范式/画像状态/触发映射/tag提案）
- **深检**（"深度健康检查"触发）：L0-L4 全层，含人工抽样

```
L0 内容层:   矛盾检测 → 时效检测(>60天) → 孤立检测 → 缺口检测
L1 资产层:   画像状态三方对齐 / 范式库完整性 / 触发映射同步 / tag提案积压
L2 画像层:   画像7维完整性 / 升级机会 / 时效性 / 画像-源材料一致性
L3 产出层:   范式-产出一致 / 画像-产出一致 / 反哺闭环审计 / 引文纪律审计 / 去AI味审计
L4 元数据层: 统计信息对齐 / 索引断链 / 文件可发现性 / 页面规模监控
```

### 4. 对比模式（修改痕迹反向建模）`NEW in v6.1`

**触发词**: "对比分析"（手动）或 Knowledge-IN Step 4 自动检测

通过我方初稿与决策者终稿的增/删/改差异，反向推演决策者的关注热点和思维模式。

```
C1: 识别对应稿件 → C2: A-F六维对比 → C3: 知识分流 → C4: 画像更新 → C5: 总体判断 → C6: 回链更新
```

**六维对比**: 新增(A) / 删除(B) / 重写(C) / 语言(D) / 知识引用(E) / 场合适配(F)

**核心洞察**: 修改痕迹的信号强度高于公开讲话——每次增/删/改都是决策者的主动选择，揭示了"他认为什么重要、什么不重要、应该从什么角度说"。

### 5. docx-formatter（公文格式调整）`NEW in v6.1`

**触发词**: "调整格式"、"docx格式"、"标准格式"

将任意 .doc/.docx 文件按中国党政公文标准格式调整，同时用修订模式标记所有内容修正。

```
读取源文件 → 分类段落(6种类型) → 识别内容问题(错别字/非标准表述)
→ 生成JSON指令清单 → 调用Python脚本生成docx → AI复检(16项清单)
→ 发现问题→修复→重新生成 → 完成
```

**核心设计**:
- **AI 做判断，脚本做执行**: AI 只输出 JSON 指令清单（段落类型 + 内容修正），Python 脚本处理全部 OOXML 细节
- **AI 复检循环**: 生成后自动解包验证 10 项格式指标 + 6 项内容指标，发现问题自动循环修复
- **修订模式**: 所有内容修正以 `<w:del>` / `<w:ins>` 标记，用户可逐条接受/拒绝
- **导出后自动验证**: `docx-validate.sh` 一键校验行间距（28pt exact）与全角引号（零半角），替代手动 grep（`NEW in v6.4`）

**支持的格式规范**: A4页面、方正小标宋标题、黑体/楷体标题、仿宋正文、28磅行距、奇偶页页码、东亚字体设置

### 6. framework-sync（框架同步）`NEW in v6.1`

**触发词**: "框架同步"、"汇总上传"、"同步框架"

将知识库工作流的演进自动汇总到 `llm-wiki-framework/` 仓库并推送 GitHub。

```
扫描源文件 → 对比已有导出 → 同步文件(含脱敏) → 更新README(架构图/能力矩阵/changelog) → Git提交推送
```

### 7. docx 导出强制流程 `NEW in v6.2`

**适用**: 任何需要导出 .docx 的场景（含 docx-formatter 输出）

针对行间距（固定值 vs 多倍行距）和引号（全角 vs 半角）两个历史高频错误，规定三段式强制流程，不可跳过：

```
Step 1 导出前 — 源 .md 文件引号检查（确认全部为中文全角 “”，无 ASCII 半角 "）
Step 2 生成中 — docx-js 代码规范（spacing 必须 line:560 + lineRule:EXACT，统一 SPACING 常量）
Step 3 导出后 — 解包 XML 检查（grep 行间距 exact / 全角引号实体 / 半角 &quot; 必须为 0）
```

> 自动化替代：`bash claude/docx-validate.sh <output.docx>` 可一键执行 Step 3（行间距 + 引号校验），`NEW in v6.4`。

### 8. 写作体系（范式 × 画像）`NEW in v6.3`

**触发词**: "撰写评论"、"撰写第一议题"、"写表态发言"、"撰写X，以Y的视角切入"、人物修改稿摄入、新体裁材料入库

写作任务统一走 `schema/4.writing-guide.md`，核心模型 = **体裁范式 × 说话人画像**——范式解决结构/格式/语言骨架，画像解决思维模式/语言风格/关注侧重（血肉），二者正交自由组合。

```
[Step 1] 解析需求（体裁+画像+主题） → [Step 2] 读范式页 → [Step 3] 加载画像
→ [Step 4] 研究思考（Grep 素材） → [Step 5] 结构设计 → [Step 6] 成文
→ [Step 7] 审校清单（含去AI味） → [Step 8] 交付 synthesis/
```

**关键规范**:
- **范式库**: `schema/4a`（第一议题表态三段式）、`schema/4b`（人民论坛时评）等，新体裁随摄入持续新增（闭环B）
- **画像库**: `schema/5.persona-guide.md` 定义 7 维建模模板，画像存于 `wiki/entities/人物-XX.md`（闭环A）
- **画像使用边界**: 复用画像的思维/侧重/话语（"像X那样想问题"），非以其名义/第一人称代笔（讲话稿类除外）
- **引文纪律六条** `CRITICAL`: CLAUDE.md §九 —— 加引号=原文照录、数据保留限定条件、跨场合语境标注、转引标注出处、政策归属准确、无源数据即废
- **去AI味规范**: `schema/4` §三-A 九项清单（破折号清零/句式去模板/动词去同质化/意象词收敛/升华腔克制/引号节制等）

---

## 核心设计决策与实战经验

以下是在真实践用约半年后沉淀的关键经验。

### 1. 为什么用 Markdown + Frontmatter 而非数据库

**决策**: 全部知识存储在 Markdown 文件中，用 YAML frontmatter 承载元数据。

**原因**:
- **LLM 原生可读**: LLM 直接读取 .md 文件，无需 SQL 查询或 API 调用
- **版本可控**: Git diff 对纯文本友好，可追踪知识的每次变更
- **互操作性**: Obsidian、VS Code、Notion 等工具都能打开
- **零运维**: 不需要数据库服务，不需要 schema migration

**代价**: 无法做复杂的关系查询。解决方案：用 Grep 全文搜索 + [[wiki链接]] 建立页面间关联。

### 2. 为什么将完成标准内嵌在步骤中

**决策**: 每一步的完成标准写在步骤描述内部（如 `✅ 完成标准：同名 .md 存在且 ≥5 行正文`），不设独立的事后检查环节。

**原因**:
- LLM 倾向于线性执行。如果检查环节独立，LLM 可能在执行完毕后"忘记"回头验证
- 将标准前置让 LLM 在每一步就有明确的"完成"定义
- 减少了需要人工确认的步骤数

**实践中发现的坑**: 最初的设计在 Step 5 之后单独设 Step 6 做"内容核查"，结果 LLM 经常在 Step 5 写入了 source 列表但不写入实际内容。将标准内嵌到 Step 5（`禁止用"更新 source 列表"替代"内容入库"`）后显著改善。

### 3. 标签体系的分层设计与增长机制

**决策**: 三级标签结构（模块→一级→二级），且 LLM 禁止捏造标签。

**原因**:
- **一致性保障**: 如果 LLM 可以自由创建标签，同一个概念会被打上不同标签名（如"产教融合"vs"校企合作"）,检索时必然遗漏
- **增长控制**: 标签可以增长，但必须通过 `open-questions` 提案 → 人工审核 → 写入字典的流程

**关键数字**: 14 个一级/实体标签 + 115 个二级标签（共 129 个注册标签）覆盖了高校管理的所有领域。这个规模在"够细"和"不过拟合"之间取得了平衡。对于其他领域，建议 8-15 个一级标签。

### 4. source 列表的置顶规则

**决策**: frontmatter 的 source 列表采用倒序排列——最新来源置顶。

**原因**: 这个看似微小的设计有实际意义。当 LLM 读取一个概念页时，source 列表的第一个就是最近更新的来源，LLM 可以直接判断"这个知识点的最新依据是什么"。如果按自然顺序（旧→新），LLM 需要翻到列表底部才能找到最新来源。

```
正确: source: [最新.md, 次新.md, 最早.md]
错误: source: [最早.md, 次新.md, 最新.md]  # LLM 无法快速定位
```

### 5. 空壳文件检测策略

**决策**: sync-log.py 不仅检测文件存在/缺失，还检测"空壳"——看起来是 .md 但实际无有效内容的文件。

**空壳来源**:
- 微信公众号分享到 Obsidian 时只保存了标题和 URL
- 网页裁剪工具只抓取了模板文字（"微信扫一扫""阅读原文"等）
- PDF 转换失败产生空文件

**检测方法**:
- 阈值法: 文件大小 < 500 bytes 且 ≤5 行正文
- 特征词法: 匹配已知平台残留文字（如"继续滑动看下一个""知道了"）

**实战价值**: 在一个 100+ 文件的 raw 目录中，这个检测每次能发现 2-5 个空壳。如果没有这个检测，LLM 会试图"学习"一个空壳文件，浪费 token 且产生无用输出。

### 6. 日志按月归档

**决策**: log.md 只保留当月记录，每月1日将上月内容移至 `wiki/log-YYYY-MM.md`。

**原因**:
- 避免单个 log.md 文件无限增长（半年的日志接近 300 行软上限）
- 保留历史可追溯性（归档而非删除）
- LLM 读 log.md 获取近期操作历史时，不需要翻过大段过期内容

### 7. 文件诊断优先于内容提取

**决策**: Knowledge-IN 流程的 Step 1 强制要求对每个文件打诊断标签（非md/链接壳/图片型/正常md），不同类型走不同预处理路径。

**原因**: 真实环境中新文件格式五花八门——PDF、Word 文档、微信分享链接壳、长图。如果跳过诊断直接提取，成功率很低。先诊断再路由，每个类型有针对性工具（pdfplumber、defuddle、Vision OCR）。

### 8. 案例材料的"双写"机制

**决策**: 案例拆解法要求同一份案例材料同时写入两个位置：entities/（机构页）+ concepts/（概念页对应板块）。

**原因**: 防止信息孤岛。如果只写 entities/，用户从概念角度检索时找不到其他机构的做法。如果只写 concepts/，无法建立"某机构有什么特色"的全局视角。

### 9. 对比模式：修改痕迹反向建模 `NEW in v6.1`

**决策**: 新增对比模式（C1-C6），通过我方初稿与决策者终稿的增/删/改差异，反向推演决策者的认知图谱。

**原因**:
- 公开讲话是决策者"想让别人看到的"，修改痕迹才是"他真正在想的"
- 每次增/删/改都是主动选择：新增揭示关注热点，删除揭示不重要/不合适的内容，重写揭示思维框架
- 传统画像依赖公开信息，对比模式补充了"负向信号"（删除）和"角度偏移"（重写）两个维度

**实战价值**: 首次执行即发现决策场合存在系统性的理论/部署比例调整模式、对标院校引用习惯、以及结尾段的稳定偏好——这些都无法从公开讲话中获取。详见 `schema/4.domain-extension-example.md`。

### 10. Agent 系统：从 Skill 到可复用 Agent `NEW in v6.1`

**决策**: 将复杂工作流封装为独立 Agent 定义文件，而非内嵌在 CLAUDE.md 中。

**原因**:
- CLAUDE.md 已接近 500 行。继续膨胀会导致 LLM 上下文过载，降低对核心规则的注意力
- Agent 定义文件是独立单元，可以单独更新、单独测试
- 每个 Agent 封装完整的"扫描→分析→执行→复检"循环，LLM 只需读取对应文件即可执行
- Agent 可以相互调用（如 framework-sync 扫描 docx-formatter Agent 的定义并将其导出）

**Agent 设计模式**:
```
[Step 1] 读取源文件 → [Step 2-N] 分析+执行 → [Step N] AI复检 → [Step N+1] 修复循环 → 完成
```

关键特征：
- 每一步有明确的 CRITICAL / IMPORTANT 优先级标记
- 最终步骤始终包含 AI 复检或用户确认
- 降级路径：主方案失败时有预设的备用方案

### 11. 写作体系：范式 × 画像的正交组合 `NEW in v6.3`

**决策**: 将写作任务建模为"体裁范式（结构骨架）× 说话人画像（思维血肉）"两个正交轴，分别存放在 `schema/4x` 与人物页，可自由组合。

**原因**:
- 传统写作指令把"结构"和"风格"揉在一起，无法复用。拆成两轴后，"第一议题用书记视角"和"第一议题用学术视角"只需换画像，不动范式
- 画像解决"像谁在说话"：复用思维方式、关注侧重、话语体系，而不是让 LLM 冒充该人物署名（评论类以作者署名，讲话稿类才代画像口吻）
- 范式库与画像库都是"吸附点"：新体裁摄入 → 建范式（闭环B）；人物修改稿摄入 → 反哺画像（闭环A）。框架随材料持续生长

**实战价值**: 画像构建不再是一次性，而是每次人物修改稿摄入时的"信号吸附"——增/删/改是本人的主动选择，比公开讲话更能揭示其真实关注。

### 12. 引文纪律：六条铁律沉淀 `NEW in v6.3`

**决策**: CLAUDE.md §九 从"source 标注格式"升级为"引文纪律六条"，每条配正误示例。

**原因**: 实测发现"有 source 不等于引法对"——常见错误包括加引号但非原文、省略数据限定条件、跨场合金句混用语境、转引未标出处、政策模式张冠李戴。

**六条**:
```
1. 加引号 = 原文照录（含标点/数据/人名），转述不得加引号
2. 数据引用保留限定条件（样本/时间/范围），不得强化对比
3. 跨场合金句须注明语境（"此前他曾指出"）
4. 转引须标注"援引/转引自"原始出处
5. 政策/模式归属准确（对象/地域/层级一致）
6. 数据无源即废 `HARD LIMIT`（宁用定性表述，不凭记忆补数字）
```

---

## 快速上手

### 前提条件

- **LLM 引擎**: Claude Code、Claude Agent SDK、或任何支持长上下文 + 工具调用的 LLM 环境
- **Python 3.6+**: 用于 sync-log.py 和 policy-organize.py 脚本
- **可选工具**: 
  - `defuddle`（网页正文提取，处理链接壳文件）
  - `pdfplumber`（PDF 文字提取）
  - 图片 OCR 工具（处理图片型文件）

### 步骤 1: 复制框架文件

```bash
cp -r llm-wiki-framework/claude/ your-project/
cp -r llm-wiki-framework/schema/ your-project/
cp -r llm-wiki-framework/templates/ your-project/
```

### 步骤 2: 初始化目录

```bash
cd your-project
mkdir -p raw/{policy,sources,practice,documents,case-studies,research,interviews}
mkdir -p wiki/{entities,concepts,synthesis}

# 从模板创建 wiki 首页和日志
cp templates/wiki-directory-structure.md wiki/index.md
```

### 步骤 3: 自定义标签体系

编辑 `schema/2.tag-index-template.md`，将标签替换为你所在领域的术语。保持三级结构（模块→一级标签→二级标签）不变。

### 步骤 4: 配置 LLM 加载规则

对于 **Claude Code**，将 `claude/CLAUDE.md` 放到项目的 `.claude/CLAUDE.md`（或通过 `--claude-md` 参数指定）。Claude 会自动将其作为项目指引加载。

对于其他 LLM 环境，将 `claude/CLAUDE.md` 和 `schema/` 目录的内容作为 system prompt 或上下文文件传入。

### 步骤 5: （可选）配置领域扩展

如果你的场景涉及特定决策者或特定类型的产出，参考 `schema/4.domain-extension-example.md` 创建领域扩展文件，并在 CLAUDE.md 的触发表中注册。

### 步骤 6: 开始摄入

1. 将原始文件放入 `raw/` 对应子目录
2. 对 LLM 说 **"同步检测"** 查看新文件
3. 对 LLM 说 **"学习新增"** 启动摄入流程
4. 定期对 LLM 说 **"健康检查"** 维护知识库质量
5. 如有对比需求，对 LLM 说 **"对比分析"** 启动修改痕迹建模

---

## 许可

MIT License. 自由使用，自由修改。

---

## 项目统计

| 指标 | 数据 |
|------|------|
| 核心脚本 | 3 个 Python 脚本 + 1 个 bash 校验脚本 (sync-log.py + policy-organize.py + docx-formatter.py + docx-validate.sh) |
| Agent 定义 | 2 个 Agent (docx-formatter + framework-sync) |
| 规范文件 | 10 个 Markdown 规范文件（含写作/画像/健康检查扩展） |
| 工作指引 | CLAUDE.md (~600行) |
| 提取方法 | 3 种基础方法 + 1 种对比模式 + 写作体系（范式×画像） |
| 触发词 | 11 个触发词覆盖 9 种工作流 |
| 标签体系 | 14 一级/实体标签 + 115 二级标签（共129注册，模板，可替换） |
| 实际运营页面 | 134 页（概念 + 实体 + 综合分析） |

---

*本框架源自一个高校管理知识库的实际运营经验（约半年），已摄入 50+ 份政策文件、40 所高校案例、20+ 篇研究资料，产出 20+ 篇综合分析报告。框架部分为从项目中独立提取，不包含任何私有数据。*

---

## Changelog

### v6.4 (2026-08-25)

- 🆕 **工作流审计优化**: A规范层 + B资产层 14 项修复（schema 文件版本/描述/目录树对齐、tag-index↔concept 双向一致核查）
- 🆕 **标签体系 v4.5**: 新增 `#人物` 实体标签（一级标签 13 + 1），新增 `#阅读素养` `#教育标准` 等二级标签，注册标签达 129 个（二级 115 个）
- 🆕 **docx-validate.sh 新脚本**: 导出后一键校验行间距（28pt exact）与全角引号（半角零容忍），替代手动 grep 复检
- 🆕 **五层健康检查 L0-L4**: `schema/6.lint-guide.md` 将健康检查从内容层升级为"内容+工作流资产+画像质量+写作产出+元数据导航"五层体系（含快检/深检两档）
- 📝 CLAUDE.md 同步至 v6.4（写作触发词、引文纪律六条、五层健康检查入口、docx 强制流程）
- 📝 schema/0.index.md 更新至 v3.4（新登记 4/4a/4b/5/6 规范文件）
- 📝 framework-sync Agent 导出映射表更新（新增 docx-validate.sh + schema/4-6 共 6 个文件）
- 📝 README 架构图/目录树/统计同步（规范文件 5 → 10，触发词 9 → 11）

### v6.3 (2026-08-17)

- 🆕 **写作体系（范式×画像）**: `schema/4.writing-guide.md` 统一写作入口（8 步流程 + 审校清单 + 去AI味规范），`schema/5.persona-guide.md` 画像 7 维建模模板，`schema/4a`/`4b` 两个初始范式页
- 🆕 **引文纪律六条**: CLAUDE.md §九 沉淀写作/摄入通用引文纪律（原文照录/限定条件/语境/转引/归属/无源即废），每条配正误示例
- 🆕 **去AI味语言规范**: `schema/4` §三-A 九项清单（破折号清零/句式去模板/动词去同质化/意象词收敛/升华腔克制/引号节制等）
- 🆕 **健康检查升级五层体系雏形**: Knowledge-LINT 从 L0 内容层扩展为 L0-L4 五层
- 📝 CLAUDE.md 新增写作触发词 5 组（撰写评论/第一议题/以Y视角/人物修改稿/新体裁），触发词 9 → 11

### v6.2 (2026-08-02)

- 🆕 **docx 导出强制流程**: CLAUDE.md 新增九-A 节，三段式强制流程（导出前引号检查 → 生成中文档编码规范 → 导出后 XML 复检），封堵行间距与引号两大高频错误
- 🆕 **标签体系 v4.3**: 新增 7 个二级标签（#全民阅读 #文化思想 #高等教育 #国家战略 #基础教育 #教育家精神 #科技创新），二级标签 106 → 113
- 📝 framework-sync / docx-formatter Agent 路径统一为 `.claude/` 相对路径（仓库可移植性）
- 📝 CLAUDE.md 同步至最新（~550 行），README 架构图与统计同步

### v6.1 (2026-07-13)

- 🆕 **docx-formatter Agent + 脚本**: 公文格式调整管道，AI 生成 JSON 指令 → Python 脚本生成 .docx → AI 复检循环
- 🆕 **framework-sync Agent**: 工作流演进自动汇总 → llm-wiki-framework → GitHub 开源同步
- 🆕 **Agent 系统**: 将复杂工作流封装为独立 Agent 定义文件（`claude/agents/`）
- 🆕 **AI 复检模式**: 生成→验证→修复循环，16 项复检清单
- 📝 CLAUDE.md 扩展至 ~500 行，新增 Agent 引用和强制前置读取规则
- 📝 触发词从 6 个增至 9 个
- 📝 schema 文件更新至最新版本

### v6.0 (2026-06-12)

- 新增指令优先级体系 (L1-L4)
- 新增模型能力边界声明
- 新增降级路径总表
- 新增 Wiki 输出格式规范

### v5.0 及更早

- Knowledge-IN/OUT/LINT 三大工作流
- 对比模式 C1-C6
- 标签体系 v4.2
- 三层分流存储策略
