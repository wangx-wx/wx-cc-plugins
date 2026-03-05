---
name: md-check
description: 扫描指定目录下的 Markdown 文件，统计指定标题等级下各段落的字符数量，展示 Top N 结果。支持在标题前后插入分隔符并输出到新目录（不修改源文件）。当用户提到 Markdown 分析、md 文件扫描、标题字符统计、内容长度排行、md 段落拆分、章节字数统计时应使用此 skill。即使用户只是说"看看哪些章节最长"或"统计一下 md 标题下的内容"，也应触发此 skill。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
---

# md-content-scanner

扫描 Markdown 文件，统计指定标题等级下的内容字符数量，展示排行榜，并可选在标题边界插入分隔符。

## 工作流程

### Step 1: 确认参数

使用 AskUserQuestion 向用户确认以下参数（提供合理默认值）：

**问题 1 - 扫描目录和标题等级：**
- 默认扫描目录：当前工作目录
- 默认标题等级：二级标题（`##`）
- 让用户确认或修改

**问题 2 - 是否插入分隔符：**
- 询问用户是否需要在指定标题等级的前后插入 `\n======\n` 分隔符
- 如果选择插入，会在新目录中生成带分隔符的副本，不修改源文件

### Step 2: 执行扫描

调用 Python 脚本进行扫描：

```bash
python <skill-path>/scripts/scan_md.py --dir <target-dir> --level <heading-level> [--top <N>]
```

参数说明：
- `--dir`：要扫描的目录路径
- `--level`：标题等级数字（1-6），例如 2 表示 `##`
- `--top`：显示前 N 个结果，默认 10
- `--recursive`：递归扫描子目录

脚本输出 JSON 格式结果，包含每个标题的文件路径、标题文本、字符数。

### Step 3: 展示结果

将脚本返回的 JSON 结果格式化为表格展示给用户：

| 排名 | 文件名 | 标题 | 字符数 |
|------|--------|------|--------|
| 1    | xxx.md | xxx  | xxx    |

### Step 4: 插入分隔符（如果用户选择了此选项）

调用脚本的插入模式：

```bash
python <skill-path>/scripts/scan_md.py --dir <target-dir> --level <heading-level> --insert-separator --output-dir <output-dir>
```

- `--insert-separator`：启用分隔符插入模式
- `--output-dir`：输出目录路径（默认在扫描目录下创建 `_separated` 子目录）

脚本会：
1. 复制所有涉及的 md 文件到输出目录（保持相对路径结构）
2. 在指定标题等级的标题行前插入 `\n======\n`
3. 在该标题段落结束处（下一个同级或更高级标题之前）插入 `\n======\n`

告知用户输出目录位置和处理的文件数量。

## 注意事项

- 字符数统计范围：从当前标题到下一个同级或更高级标题之间的纯文本内容，不包含子标题及其下属内容
- 统计时去除空行和前后空白，只计算实际文本字符
- 分隔符插入不修改源文件，所有改动输出到新目录
