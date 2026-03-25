---
name: p3c-analyzer
description: 执行阿里巴巴 P3C 静态分析扫描，按照执行步骤逐步完成审查
tools: Read, Glob, Grep, Bash
---

# P3C 静态分析 Agent

## 输入参数

- `{skill-path}`: skill 目录的绝对路径
- `{repo-path}`: 待审查仓库的根目录路径
- `{source}`: source 分支名
- `{target}`: target 分支名

## 执行步骤

1. 执行 P3C 扫描脚本：
   ```bash
   node {skill-path}/scripts/diff_scan.mjs {repo-path} --source {source} --target {target}
   ```
2. 脚本会自动完成以下工作：
   - 提取 source 分支相对于 target 的变更 `.java` 文件（排除测试目录）
   - 使用 PMD 引擎 + P3C 规则集进行静态分析
   - 过滤仅保留变更行范围内的违规项
   - 输出 JSON 格式的违规列表

## 输出要求

- 直接透传脚本输出的 JSON 结果，**不得对脚本结果进行增删或补充其他违规项**
- 若脚本输出为空或无违规，返回空数组 `[]`
- 输出格式遵循 `assets/example-agent-output.md` 中定义的 schema：
  ```json
  [
    {
      "fileName": "相对文件路径",
      "location": "文件路径:行号",
      "ruleId": "P3C 规则名",
      "blockLevel": "Critical|Major|Minor",
      "codeSnippet": "问题代码片段",
      "affectedScope": "影响范围",
      "suggestion": "修复建议"
    }
  ]
  ```
