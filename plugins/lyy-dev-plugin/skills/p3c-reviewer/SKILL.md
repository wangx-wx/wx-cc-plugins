---
name: p3c-reviewer
description:  基于阿里巴巴 P3C 规范的代码审查工具，通过 PMD 静态分析引擎检查代码规范问题。使用场景：(1) 用户要求进行 P3C 代码审查或规范检查，(2) 用户要求对比两个 Git 分支的变更文件并进行代码审查，(3) 用户提及阿里巴巴编码规范、Java 编码规范检查。支持增量审查（仅扫描分支差异文件）和全量审查（指定文件/目录）。
allowed-tools:
  - Bash(git rev-parse *)
  - Bash(python *git_diff_files.py*)
  - Bash(python *batch_scan_files.py*)
  - Bash(python *scan_project.py*)
---

# P3C Reviewer

基于阿里巴巴 P3C 规范，通过 PMD 引擎对代码执行静态分析。默认使用增量模式，仅当用户明确要求全量检查时切换到全量模式。

## 工作流

### 1. 增量审查（默认）

对比两个 Git 分支的变更文件，仅扫描差异部分。

**步骤 1：确认分支信息**

通过 `git rev-parse --abbrev-ref HEAD` 获取当前分支名作为 source 默认值，target 默认值为 `origin/master`。使用 AskUserQuestion 让用户确认或修改：
- **source 分支**：默认当前分支
- **target 分支**：默认 `origin/master`
- **仓库路径**：默认当前工作目录

**步骤 2：获取变更文件**

执行脚本，获取P3C审查报告，将报告的结果返回
```bash
python <skill-path>/scripts/diff_scan.py <repo-path> --source <source-branch> --target <target-branch>
```

默认优先级为 2（输出 Blocker、Critical、Major 级违规）。仅当用户明确要求调整优先级时才添加 `--priority <level>` 参数。

### 2. 全量审查（用户明确要求时）

扫描整个项目或指定目录，自动发现 Maven 多模块并逐模块扫描。

```bash
python <skill-path>/scripts/scan_project.py <project-dir>
```

参数说明：
- `--priority <level>`：仅当用户要求调整时添加
- `--no-recursive`：禁用 pom.xml 递归，仅兜底扫描
- `--list-modules`：仅列出模块不执行扫描，用于让用户预览

### 3. 生成审查报告

将 JSON 结果转为 Markdown 表格报告。报告模板参见 [references/example-output.md](references/example-output.md)。

若无违规，输出"未发现违规项"。
