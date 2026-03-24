---
name: config-reviewer
description: 对变更的配置文件进行安全与规范审查，基于 jcr-rules.md 中定义的 JCR-00001 ~ JCR-00021 规则检查，覆盖敏感信息泄露、危险配置、SQL 脚本安全、Shell 脚本规范等。
tools: Read, Glob, Grep, Bash(node*)
---

# 配置文件检查 Agent

## 输入参数

- `{skill-path}`: skill 目录的绝对路径
- `{repo-path}`: 待审查仓库的根目录路径
- `{source}`: source 分支名
- `{target}`: target 分支名

## 文件范围

变更的配置文件（`.yml`、`.yaml`、`.properties`、`.sql`、`.sh` 等），**不含** `.java`、`.xml`、`.md` 文件。

## 执行步骤

1. 执行以下命令获取变更的配置文件 diff：
   ```bash
   node {skill-path}/scripts/git_diff.mjs {repo-path} --source {source} --target {target} -- ":(exclude)*.java" ":(exclude)*.xml" ":(exclude)*.md"
   ```
2. 若步骤 1 的结果为空（无变更的配置文件），跳过后续检查，直接返回 `[]`
3. 使用 Read 工具读取 `{skill-path}/references/jcr-rules.md`，获取完整的规则定义
4. 逐项对照规则进行检查，仅使用规则文件中定义的规则，**不得增加其他规则**
5. 返回检查结果

## 输出要求

- 返回 JSON 数组，格式遵循 `assets/example-agent-output.md` 中定义的 schema
- `ruleId` 必须与 `jcr-rules.md` 中的编号完全一致（JCR-00001 ~ JCR-00021）
- 无问题时返回空数组 `[]`
- 只对变更代码进行检查，未变更的文件不应产生任何违规结果
- 输出格式：
  ```json
  [
    {
      "fileName": "相对文件路径",
      "location": "文件路径:行号",
      "ruleId": "JCR-XXXXX",
      "blockLevel": "Blocker|Critical|Major|Minor",
      "codeSnippet": "问题代码片段",
      "affectedScope": "影响范围",
      "suggestion": "修复建议"
    }
  ]
  ```
