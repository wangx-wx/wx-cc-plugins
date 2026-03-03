---
name: java-code-review
description: 对已有的 Java 代码进行审查，以确保其可重复使用性、质量和效率，然后生成审查报告。
allowed-tools:
  - Bash(git diff *)
  - Bash(git rev-parse *)
  - Bash(python *diff_scan.py*)
---

# Java Code Review

对所有修改过的文件进行检查，对其进行P3C、基础规范、配置文件、XML和自定义规范审查，生成审查报告。

## 阶段1 确认分支信息
通过 `git rev-parse --abbrev-ref HEAD` 获取当前分支名作为 <source>source</source> 默认值，target 默认值为 <target>`origin/master`</target>。使用 AskUserQuestion 让用户确认或修改：
- **source 分支**：默认当前分支
- **target 分支**：默认 `origin/master`
- **仓库路径**：默认当前工作目录

## 阶段2 并行启动 4 个 Review Agents
使用`Task Tool`同时启动4个Agents，分别独立审查变更。每一个代理都有`Bash(git diff *)`的权限，将<source>分支</source>、<target>分支</target>、本地仓库地址信息完整的传递给子代理

### Agent 1: P3C 审查
`Agent 1` 拥有`Bash(python *diff_scan.py*)`权限
执行脚本，获取P3C审查报告，将报告的结果返回
```bash
python <skill-path>/scripts/diff_scan.py <repo-path> --source <source-branch> --target <target-branch>W
```

### Agent 2: 基础规范审查
1. 执行`git diff <source>分支</source> <target>分支</target> -- "*.java" ":(exclude)*.md"`命令获取所有变更的Java文件
2. 无变更文件则返回`[]`，对于所有变更文件执行规范检查，检查内容仅限于[references/base-rules.md](references/base-rules.md)
3. 最后返回检查报告，报告格式参考：[assets/example-agent-output.md](assets/example-agent-output.md)

### Agent 3: 配置文件检查
1. 执行`git diff <source>分支</source> <target>分支</target> -- ":(exclude)*.java" ":(exclude)*.xml" ":(exclude)*.md"`命令获取所有变更的配置文件
2. 无变更文件则返回空`[]`，对于所有变更文件执行规范检查，检查内容仅限于[references/jcr-rules.md](references/jcr-rules.md)
3. 最后返回检查报告，报告格式参考：[assets/example-agent-output.md](assets/example-agent-output.md)

### Agent 4: 数据库XML检查
1. 执行`git diff <source>分支</source> <target>分支</target> -- "*.xml" ":(exclude)*pom.xml" ":(exclude)*.md"`命令获取所有变更的orm xml文件
2. 无变更文件则返回空`[]`，对于所有变更文件执行规范检查，检查内容仅限于[references/sql-xml-rules.md](references/sql-xml-rules.md)
3. 最后返回检查报告，报告格式参考：[assets/example-agent-output.md](assets/example-agent-output.md)


## 阶段3 输出检查报告

根据所有Agent返回的检查信息进行总结汇总，输出一份报告，报个格式参考：[assets/example-output.md](assets/example-output.md)。