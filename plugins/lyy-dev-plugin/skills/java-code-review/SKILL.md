---
name: java-code-review
description: 对已有的 Java 代码进行审查，以确保其可重复使用性、质量和效率，然后生成审查报告。当用户提到代码审查、review、代码检查、合并前审查、MR 审查、PR 审查、代码质量检查、P3C 检查、Java 规范检查时，应使用此 skill。即使用户只是说"帮我看看代码"或"检查一下改动"，只要上下文是 Java 项目，都应触发此 skill。
disable-model-invocation: true
allowed-tools: Bash(git diff *), Bash(git rev-parse *),  Bash(git show-ref *), Bash(git fetch *), Bash(python *diff_scan.py*), Bash(python3 *diff_scan.py*), Read, Grep, Glob, AskUserQuestion, Bash(mkdir *), Bash(date *), Write
---

# Java Code Review

对两个分支之间所有变更文件进行多维度审查（P3C 静态分析、基础规范、配置文件、数据库 XML），最终生成一份结构化的审查报告。

## 阶段1：确认分支信息

1. 若 `$ARGUMENTS[0]` 非空，执行 `git show-ref --verify refs/heads/$ARGUMENTS[0] || git show-ref --verify refs/remotes/$ARGUMENTS[0]`，命令成功则 `{source}` = `$ARGUMENTS[0]`
2. 若 `$ARGUMENTS[1]` 非空，执行 `git show-ref --verify refs/heads/$ARGUMENTS[1] || git show-ref --verify refs/remotes/$ARGUMENTS[1]`，命令成功则 `{target}` = `$ARGUMENTS[1]`
3. 若 `{source}` 和 `{target}` 均已设置，跳过第 4-6 步直接继续
4. 执行 `git rev-parse --abbrev-ref HEAD` 获取当前分支名，作为 `{source}` 的默认值
5. `{target}` 默认值设为 `origin/master`，`{repo}` 默认值设为当前工作目录
6. 使用 AskUserQuestion 让用户确认或修改以下信息：
   - **source 分支**：默认当前分支
   - **target 分支**：默认 `origin/master`
   - **仓库路径**：默认当前工作目录

> 后续阶段中，`{source}` 代表最终确定的 source 分支，`{target}` 代表最终确定的 target 分支，`{repo-path}` 代表仓库路径。

## 阶段2：并行启动 4 个 Review Agents

使用 ${AGENT_TOOL_NAME} tool 在一条消息中同时启动 4 个代理（`subagent_type: "general-purpose"`），每个代理独立完成各自的检查任务并返回结果，主 Agent 不参与具体的检查过程，仅负责收集结果。在 prompt 中将 `{source}`、`{target}`、`{repo-path}` 完整传递给每个子代理。

每个子代理返回的结果是 JSON 数组，格式遵循 [assets/example-agent-output.md](assets/example-agent-output.md) 中定义的 schema。无问题时返回空数组 `[]`。

> **规则约束**：
> 1. 每个子代理必须先读取对应的参考规则文件，仅使用文件中定义的规则进行检查，返回结果中的 ruleId 必须与参考文件中的编号完全一致。
> 2. 只对变更文件进行检查，未变更的文件不应产生任何违规结果。
> 3. 每个子代理拥有 Bash(git diff \*)、Bash(git rev-parse \*)、Bash(git fetch \*)、Bash(python \*diff_scan.py\*)、Read、Grep、Glob 等工具权限。

### Agent 1：P3C 静态分析（子代理独立完成）

子代理执行 P3C 扫描脚本，独立完成静态分析并返回结果：

```bash
python <skill-path>/scripts/diff_scan.py {repo-path} --source {source} --target {target}
```

脚本输出 JSON 格式违规列表，子代理直接透传结果，**不得对脚本结果进行增删或补充其他违规项**。

### Agent 2：Java规范检查（子代理独立完成）

**文件范围**：所有变更的 `.java` 文件（排除单元测试目录）

子代理独立执行以下步骤，将以下步骤完全转交给子代理：

1. 执行 `git diff {target}...{source} -- "*.java" ":(exclude)*/src/test/*"` 获取变更的 Java 文件（排除单元测试目录）
2. 步骤 1 的结果为空，足以证明若无变更文件，返回 `[]`，不需要做其他检查
3. 使用 Read 工具读取 `<skill-path>/references/java-rules.md`，获取完整的规则，不需要增加其他规则
4. 对每个变更文件：
   - **以 diff hunk 中 `+` 开头的行作为主要检查对象**，这些是本次变更引入的新增或修改内容
   - 若规则需要统计整个文件结构（如方法行数、类行数），使用 Read 工具读取完整文件作为**上下文参考**，但违规结论必须是"本次变更导致该规则被触发"，而非历史存量问题
   - 逐项对照步骤 3 中的规则进行检查
5. 返回检查报告，格式参考 [assets/example-agent-output.md](assets/example-agent-output.md)

### Agent 3：配置文件检查（子代理独立完成）

**文件范围**：变更的配置文件（`.yml`、`.yaml`、`.properties`、`.sql`、`.sh` 等，**不含** `.java`、`.xml`、`.md`）  

子代理独立执行以下步骤，将以下步骤完全转交给子代理：

1. 执行 `git diff {target}...{source} -- ":(exclude)*.java" ":(exclude)*.xml" ":(exclude)*.md"` 获取变更的配置文件（.yml/.yaml/.properties/.sql/.sh 等）
2. 步骤 1 的结果为空，足以证明若无变更文件，返回 `[]`，不需要做其他检查
3. 使用 Read 工具读取 `<skill-path>/references/jcr-rules.md`，获取完整的规则，不需要增加其他规则
4. 对每个变更文件：
   - **以 diff hunk 中 `+` 开头的行作为主要检查对象**
   - 逐项对照步骤 3 中的规则进行检查
5. 返回检查报告，格式参考 [assets/example-agent-output.md](assets/example-agent-output.md)

### Agent 4：数据库 XML 检查（子代理独立完成）

**文件范围**：变更的 ORM XML 文件（如 MyBatis mapper，**不含** `pom.xml`）  
子代理独立执行以下步骤，将以下步骤完全转交给子代理：

1. 执行 `git diff {target}...{source} -- "*.xml" ":(exclude)*pom.xml"` 获取变更的 ORM XML 文件（如 MyBatis mapper）
2. 步骤 1 的结果为空，足以证明若无变更文件，返回 `[]`，不需要做其他检查
3. 使用 Read 工具读取 `<skill-path>/references/sql-xml-rules.md`，获取完整的规则，不需要增加其他规则
4. 对每个变更文件：
   - **以 diff hunk 中 `+` 开头的行作为主要检查对象**
   - 逐项对照步骤 3 中的规则进行检查
5. 返回检查报告，格式参考 [assets/example-agent-output.md](assets/example-agent-output.md)

## 阶段3：汇总输出并保存审查报告

收集所有 Agent 返回的 JSON 数组结果，按以下步骤生成最终报告：

1. **合并结果**：将 4 个 Agent 的 JSON 数组合并为一个结果报告
2. **分级排列**：按 `blockLevel` 严重程度排序：Blocker → Critical → Major → Minor
3. **生成报告**：按照 [assets/example-output.md](assets/example-output.md) 的格式输出最终 Markdown 报告，包含：
   - 审查范围（分支信息）
   - 统计（每个级别的问题数量）
   - 优势（变更中做得好的方面）
   - 按级别分组的问题展示（每个问题包含规则编号、位置、代码片段、影响、修复建议）
      - P3C 违规问题展示时，需要标记是P3C检查结果
   - 清单覆盖情况
   - 建议
   - 是否可合并的评估结论
4. **保存报告到文件**：
   - 执行 `date +%Y%m%d%H%M%S` 获取当前时间戳（格式：年月日时分秒，如 `20260312143025`）
   - 在 `{repo-path}` 下创建目录：`mkdir -p {repo-path}/data/{timestamp}`
   - 使用 Write 工具将报告保存到：`{repo-path}/data/ai-code-review/{timestamp}/代码审查报告.md`
   - 告知用户报告已保存的完整路径
