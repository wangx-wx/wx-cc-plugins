# Java-Code-Review Skills 介绍

基于 Claude Code 的 Java 代码审查 Skill，通过多 Agent 并行架构对分支变更进行多维度自动化审查，生成结构化的审查报告。

## 使用方式

### 方式一：自然语言触发

在 Claude Code 中输入以下任意指令，Skill 会自动识别并启动：

```
帮我审查一下代码
检查一下这个分支的改动
review 一下当前的变更
做一次代码审查
```

### 方式二：Skill 命令调用

```bash
/java-code-review source_branch target_branch
```

### 方式三：直接执行 Skill

```bash
/java-code-review
```

不带参数直接执行，Skill 会自动检测当前分支信息并让用户确认后开始审查。

### 执行流程

1. **确认分支信息** - Skill 自动检测当前分支并让用户确认
2. **并行审查** - 启动 4 个 Agent 并行执行审查
3. **生成报告** - 汇总结果、去重、按严重级别排序输出


## 工作流程

```
┌─────────────────────────────────────┐
│  阶段1：确认分支信息                   │
│  source 分支 / target 分支 / 仓库路径  │
└──────────────┬──────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│  阶段2：并行启动 4 个 Review Agents                        │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Agent 1  │ │ Agent 2  │ │ Agent 3  │ │  Agent 4   │  │
│  │ P3C 静态 │ │ Java规范 │ │ 配置文件 │ │ 数据库 XML │  │
│  │ 分析     │ │ 检查     │ │ 检查     │ │ 检查       │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘  │
│       │            │            │              │         │
└───────┼────────────┼────────────┼──────────────┼─────────┘
        │            │            │              │
        ▼            ▼            ▼              ▼
┌──────────────────────────────────────────────────────────┐
│  阶段3：合并 → 去重 → 分级排列 → 生成审查报告              │
└──────────────────────────────────────────────────────────┘
```

## 审查维度

| Agent | 审查范围 | 检查方式 | 规则文件 |
|-------|---------|---------|---------|
| P3C 静态分析 | 变更的 `.java` 文件 | PMD 引擎扫描 | 阿里巴巴 P3C 规则集 |
| Java 规范检查 | 变更的 `.java` 文件 | AI 逐规则审查 | `references/java-rules.md` |
| 配置文件检查 | `.yml` `.properties` `.sql` `.sh` 等 | AI 逐规则审查 | `references/jcr-rules.md` |
| 数据库 XML 检查 | MyBatis mapper 等 `.xml`（排除 pom.xml） | AI 逐规则审查 | `references/sql-xml-rules.md` |

## 目录结构

```
java-code-review/
├── SKILL.md                          # Skill 主指令文件
├── README.md                         # 本文件
├── assets/
│   ├── example-agent-output.md       # Agent 输出 JSON Schema 及示例
│   └── example-output.md             # 最终审查报告模板
├── references/
│   ├── java-rules.md                 # Java 规范规则
│   ├── jcr-rules.md                  # 配置文件与脚本规则
│   └── sql-xml-rules.md              # 数据库 XML 规则（MyBatis）
└── scripts/
    ├── diff_scan.mjs                 # P3C 差异扫描脚本
    ├── git_diff.mjs                  # Git diff 包装脚本
    └── lib/                          # PMD + P3C 依赖 JAR
```

## 环境要求

- **Git**：用于分支差异对比
- **Java（JDK/JRE）**：P3C 静态分析依赖 PMD 引擎
- **Node.js**：运行 `diff_scan.mjs` 和 `git_diff.mjs` 脚本

## 权限配置（推荐）

审查过程中需要执行 Bash 命令（如 git diff、P3C 扫描等），建议提前配置权限以避免频繁确认弹窗。以下两种方式二选一：

### 方式一：用户级配置（推荐）

编辑 `~/.claude/settings.json`：

```json
{
  "permissions": {
    "allow": [
      "Bash"
    ]
  }
}
```

### 方式二：项目级配置

编辑项目根目录下 `.claude/settings.local.json`：

```json
{
  "permissions": {
    "allow": [
      "Bash"
    ]
  }
}
```