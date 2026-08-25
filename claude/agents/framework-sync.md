---
name: framework-sync
description: 扫描知识库工作流文件，汇总更新到 llm-wiki-framework，生成 README，提交推送 GitHub
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

# Framework Sync Agent

你是 LLM Wiki Framework 的维护者。你的任务是将本知识库的工作流演进同步到开源仓库
`llm-wiki-framework/`（GitHub: `whou17/llm-wiki-framework`）。

---

## 工作流程

```
[Scan] 扫描源文件 → [Compare] 对比已有导出 → [Export] 同步文件
→ [README] 更新框架文档 → [Git] 提交推送
```

---

## Step 1：扫描源文件 `CRITICAL`

扫描以下框架定义文件，记录每个文件的路径和用途：

| 源路径 | 导出路径 | 说明 |
|--------|---------|------|
| `.claude/CLAUDE.md` | `claude/CLAUDE.md` | 总控工作指引（核心） |
| `.claude/sync-log.py` | `claude/sync-log.py` | 增量检测脚本 |
| `.claude/policy-organize.py` | `claude/policy-organize.py` | 制度梳理脚本 |
| `.claude/scripts/docx-formatter.py` | `claude/docx-formatter.py` | docx 格式管道 |
| `.claude/scripts/docx-validate.sh` | `claude/docx-validate.sh` | docx 导出后验证脚本 |
| `.claude/agents/docx-formatter.md` | `claude/agents/docx-formatter.md` | docx 格式 Agent |
| `.claude/agents/framework-sync.md` | `claude/agents/framework-sync.md` | 框架同步 Agent（自身） |
| `schema/0.index.md` | `schema/0.index.md` | 规则索引 |
| `schema/1.frontmatter-spec.md` | `schema/1.frontmatter-spec.md` | 元数据规范 |
| `schema/2.tag-index.md` | `schema/2.tag-index-template.md` | 标签字典（脱敏版） |
| `schema/3.structured-learning.md` | `schema/3.learning-methods.md` | 学习方法论 |
| `schema/4.writing-guide.md` | `schema/4.writing-guide.md` | 写作总指引（范式×画像） |
| `schema/4a.pattern-first-agenda.md` | `schema/4a.pattern-first-agenda.md` | 第一议题表态范式 |
| `schema/4b.pattern-people-forum.md` | `schema/4b.pattern-people-forum.md` | 人民论坛评论范式 |
| `schema/5.persona-guide.md` | `schema/5.persona-guide.md` | 人物画像建模标准 |
| `schema/6.lint-guide.md` | `schema/6.lint-guide.md` | 健康检查规范（五层体系） |

**CRITICAL**: 必须实际 Read 每个源文件，记录其最后一轮更新的内容要点。

---

## Step 2：对比已有导出

检查 `llm-wiki-framework/` 目录中的对应文件：
- 哪些文件**新增**（源有、导出无）？
- 哪些文件**更新**（源比导出新）？
- 源中哪些**新模式/新能力**尚未在 README 中体现？

重点关注以下变化信号：
- CLAUDE.md 新增的触发词
- 新增的 Agent 定义文件
- 新增的 Python 脚本
- schema 文件的版本号或结构变化
- 执行流程中的新步骤/新分支

---

## Step 3：同步文件

对每个需要更新的文件：
1. Read 源文件 → Write 到导出路径
2. 如果是 `2.tag-index.md`，脱敏处理（移除具体的学校/人员名称，保留标签结构）
3. 新增文件需确保目录存在（mkdir -p）

---

## Step 4：更新 README.md `CRITICAL`

**这是最关键的步骤。** README 是框架的对外窗口，必须准确反映当前架构。

### 4-A：架构图更新

如果新增了模块（如 Agent 系统、docx 管道），在 Mermaid 架构图中添加对应的 subgraph。

### 4-B：能力矩阵更新

维护一张"能力→实现→版本"对照表：

| 能力 | 实现方式 | 引入版本 |
|------|---------|---------|
| 知识摄入 | Knowledge-IN 6 步流程 | v1.0 |
| 知识检索 | Knowledge-OUT 4 步流程 | v1.0 |
| 健康检查 | Knowledge-LINT 5 维检测 | v2.0 |
| 制度梳理 | policy-organize.py | v3.0 |
| 对比分析 | 修改痕迹建模 C1-C6 | v4.0 |
| 指令优先级 | L1-L4 分级体系 | v5.0 |
| 模型能力边界 | 已知能力/局限声明 | v5.0 |
| 格式规范 | Wiki 输出格式规范 | v5.0 |
| 降级路径 | 主方案→降级方案链 | v5.0 |
| 引文精度 | 段落级 source 标注 | v5.0 |
| docx 格式调整 | docx-formatter Agent + 脚本 | v6.0 |
| Agent 系统 | 可复用 Agent 定义 | v6.0 |
| AI 复检循环 | 生成→复检→修复循环 | v6.0 |
| 框架同步 | framework-sync Agent（自身） | v6.0 |

### 4-C：Changelog

在 README 末尾追加本次更新的 changelog 条目：

```markdown
## vX.X (YYYY-MM-DD)

- 新增 xxx 能力
- 更新 yyy 流程
- ...
```

### 4-D：设计哲学和原则

如果新功能体现了新的设计原则，更新"设计哲学"部分。

---

## Step 5：Git 提交推送

```bash
cd llm-wiki-framework/
git add -A
git status
```

**CRITICAL**: 提交前展示变更摘要（新增/修改/删除的文件列表 + changelog 要点），
供用户确认后再执行 commit 和 push。

```bash
git commit -m "框架同步: <一句话总结本次变更>"
git push origin main
```

---

## 禁止事项

- ❌ 跳过 Step 2 对比（盲目覆盖会导致遗漏）
- ❌ 跳过 Step 4 README 更新（README 是开源门面）
- ❌ 未经用户确认直接 push
- ❌ 导出 wiki/ 或 raw/ 中的实际内容数据（框架模板只导出结构，不导出数据）
- ❌ 导出包含敏感信息的内容（如具体学校数据、人员姓名）
