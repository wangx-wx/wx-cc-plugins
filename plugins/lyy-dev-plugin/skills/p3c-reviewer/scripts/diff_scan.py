"""Git 分支差异扫描 + P3C 代码审查合并脚本

功能:
- 获取两个分支之间的变更文件
- 对变更文件执行 P3C 检查
- 转换输出格式为简化数组
- 支持优先级过滤（默认 2 级）
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SCRIPT_DIR, "lib")

P3C_RULESETS = [
    "rulesets/java/ali-comment.xml",
    "rulesets/java/ali-concurrent.xml",
    "rulesets/java/ali-constant.xml",
    "rulesets/java/ali-exception.xml",
    "rulesets/java/ali-flowcontrol.xml",
    "rulesets/java/ali-naming.xml",
    "rulesets/java/ali-oop.xml",
    "rulesets/java/ali-orm.xml",
    "rulesets/java/ali-other.xml",
    "rulesets/java/ali-set.xml",
]

# Priority 到 BlockLevel 的映射
PRIORITY_TO_BLOCK_LEVEL = {
    1: "Critical",
    2: "Critical",
    3: "Major",
    4: "Minor",
    5: "Info",  # 可选
}


# ---------------------------------------------------------------------------
# Git 仓库验证（来自 git_diff_files.py）
# ---------------------------------------------------------------------------

def validate_git_repo(repo_path: str) -> str:
    """验证路径为有效 Git 仓库，返回绝对路径。

    Args:
        repo_path: 仓库路径

    Returns:
        仓库的绝对路径

    Raises:
        SystemExit: 路径不存在或非 Git 仓库
    """
    abs_path = os.path.abspath(repo_path)
    if not os.path.isdir(abs_path):
        raise SystemExit(f"路径不存在或不是目录: {abs_path}")
    git_dir = os.path.join(abs_path, ".git")
    if not os.path.exists(git_dir):
        raise SystemExit(f"不是有效的 Git 仓库（未找到 .git）: {abs_path}")
    return abs_path


def validate_branch_exists(repo_path: str, branch: str) -> None:
    """验证分支在仓库中存在。

    Args:
        repo_path: 仓库绝对路径
        branch: 分支名

    Raises:
        SystemExit: 分支不存在或 git 不可用
    """
    cmd = ["git", "-C", repo_path, "rev-parse", "--verify", branch]
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError:
        raise SystemExit("git 命令未找到，请确认已安装 Git 并加入 PATH")
    if proc.returncode != 0:
        stderr_str = proc.stderr.decode("gbk", errors="replace").strip()
        raise SystemExit(f"分支不存在: {branch}\n  {stderr_str}")


# ---------------------------------------------------------------------------
# Git diff 执行（来自 git_diff_files.py）
# ---------------------------------------------------------------------------

def get_diff_file_statuses(
    repo_path: str, source: str, target: str
) -> List[Tuple[str, str]]:
    """执行 git diff 获取变更文件及其状态。

    使用三点语法 target...source 获取 source 相对 target 引入的变更。

    Args:
        repo_path: 仓库绝对路径
        source: 源分支（feature 分支）
        target: 目标分支（main/master）

    Returns:
        [(status, relative_path), ...] 列表

    Raises:
        SystemExit: git 命令执行失败
    """
    cmd = [
        "git", "-C", repo_path,
        "diff", "--name-status", f"{target}...{source}",
    ]
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError:
        raise SystemExit("git 命令未找到，请确认已安装 Git 并加入 PATH")

    stderr_str = proc.stderr.decode("gbk", errors="replace").strip()
    if proc.returncode != 0:
        raise SystemExit(f"git diff 执行失败:\n  {stderr_str}")
    if stderr_str:
        for line in stderr_str.splitlines()[:5]:
            print(f"  [WARN] {line}", file=sys.stderr)

    stdout_str = proc.stdout.decode("utf-8", errors="replace")
    results: List[Tuple[str, str]] = []
    for line in stdout_str.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            results.append((parts[0].strip(), parts[1].strip()))
    return results


# ---------------------------------------------------------------------------
# 文件过滤与路径解析（来自 git_diff_files.py）
# ---------------------------------------------------------------------------

def filter_changed_files(file_statuses: List[Tuple[str, str]]) -> List[str]:
    """过滤出非删除状态的变更文件。

    Args:
        file_statuses: [(status, path), ...] 列表

    Returns:
        相对路径列表
    """
    return [
        path for status, path in file_statuses
        if not status.startswith("D")
    ]


def resolve_absolute_paths(
    repo_path: str, relative_paths: List[str]
) -> List[str]:
    """将相对路径转为绝对路径，跳过不存在的文件并发出警告。

    Args:
        repo_path: 仓库绝对路径
        relative_paths: 相对于仓库根目录的文件路径列表

    Returns:
        存在的文件的绝对路径列表
    """
    absolute_paths: List[str] = []
    for rel_path in relative_paths:
        abs_path = os.path.normpath(os.path.join(repo_path, rel_path))
        if os.path.isfile(abs_path):
            absolute_paths.append(abs_path)
        else:
            print(
                f"  [WARN] 文件在工作区中不存在（可能未切换到 source 分支）: {rel_path}",
                file=sys.stderr,
            )
    return absolute_paths


# ---------------------------------------------------------------------------
# classpath（来自 batch_scan_files.py）
# ---------------------------------------------------------------------------

def build_classpath() -> str:
    """构建 PMD 和 P3C 的 classpath。

    Returns:
        由分隔符连接的 JAR 文件路径字符串
    """
    jars = glob.glob(os.path.join(LIB_DIR, "*.jar"))
    if not jars:
        raise FileNotFoundError(f"lib 目录下未找到 jar 文件：{LIB_DIR}")
    return os.pathsep.join(jars)


# ---------------------------------------------------------------------------
# PMD 执行（来自 batch_scan_files.py）
# ---------------------------------------------------------------------------

def run_p3c_check(source_path: str) -> str:
    """对单个文件执行 PMD 检查。

    Args:
        source_path: 文件路径

    Returns:
        JSON 格式的检查报告字符串
    """
    classpath = build_classpath()
    cmd = [
        "java", "-cp", classpath,
        "net.sourceforge.pmd.PMD",
        "-d", source_path,
        "-R", ",".join(P3C_RULESETS),
        "-f", "json",
        "--encoding", "UTF-8",
    ]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_str = proc.stdout.decode("utf-8", errors="replace")
    stderr_str = proc.stderr.decode("utf-8", errors="replace")

    if stderr_str:
        for line in stderr_str.strip().splitlines()[:5]:
            print(f"  [WARN] {line}", file=sys.stderr)

    return stdout_str


# ---------------------------------------------------------------------------
# JSON 合并（来自 batch_scan_files.py）
# ---------------------------------------------------------------------------

def merge_reports(json_contents: List[str]) -> Dict[str, Any]:
    """合并多个 JSON 报告为一个。

    Args:
        json_contents: JSON 报告字符串列表

    Returns:
        合并后的 JSON 对象
    """
    merged_files: List[Dict[str, Any]] = []
    seen_files: set = set()

    for json_content in json_contents:
        if not json_content.strip():
            continue

        try:
            data = json.loads(json_content)
            files = data.get("files", [])
            for file_entry in files:
                filename = file_entry.get("filename")
                if filename and filename not in seen_files:
                    seen_files.add(filename)
                    merged_files.append(file_entry)
        except json.JSONDecodeError:
            continue

    return {"files": merged_files}


# ---------------------------------------------------------------------------
# 优先级过滤（来自 batch_scan_files.py）
# ---------------------------------------------------------------------------

def filter_by_priority(
    data: Dict[str, Any], max_priority: int = 2
) -> Dict[str, Any]:
    """过滤 JSON 报告，仅保留指定优先级以下的违规项。

    Args:
        data: JSON 报告对象
        max_priority: 最大优先级（保留 priority <= max_priority 的项）

    Returns:
        过滤后的 JSON 对象
    """
    filtered_files: List[Dict[str, Any]] = []

    for file_entry in data.get("files", []):
        filename = file_entry.get("filename", "")
        violations = file_entry.get("violations", [])

        filtered_violations = [
            v for v in violations
            if v.get("priority", 5) <= max_priority
        ]

        if filtered_violations:
            filtered_files.append({
                "filename": filename,
                "violations": filtered_violations
            })

    return {"files": filtered_files}


# ---------------------------------------------------------------------------
# 格式转换（新增）
# ---------------------------------------------------------------------------

def transform_to_output_format(
    data: Dict[str, Any],
    repo_path: str
) -> List[Dict[str, Any]]:
    """将 PMD JSON 报告转换为简化的输出格式。

    Args:
        data: PMD JSON 报告对象
        repo_path: 仓库路径（用于将绝对路径转为相对路径）

    Returns:
        简化格式的违规项列表
    """
    results: List[Dict[str, Any]] = []

    for file_entry in data.get("files", []):
        filename = file_entry.get("filename", "")

        # 将绝对路径转为相对于仓库的路径
        try:
            rel_path = os.path.relpath(filename, repo_path)
        except ValueError:
            rel_path = filename

        for violation in file_entry.get("violations", []):
            priority = violation.get("priority", 5)
            results.append({
                "fileName": rel_path,
                "beginline": violation.get("beginline", 0),
                "begincolumn": violation.get("begincolumn", 0),
                "endline": violation.get("endline", 0),
                "endcolumn": violation.get("endcolumn", 0),
                "suggestion": violation.get("description", ""),
                "ruleId": violation.get("rule", ""),
                "blockLevel": PRIORITY_TO_BLOCK_LEVEL.get(priority, "Info"),
            })

    return results


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def diff_scan(
    repo_path: str,
    source: str,
    target: str,
    max_priority: int = 2
) -> List[Dict[str, Any]]:
    """执行分支差异扫描。

    Args:
        repo_path: Git 仓库路径
        source: 源分支
        target: 目标分支
        max_priority: 最大优先级（过滤阈值）

    Returns:
        简化格式的违规项列表
    """
    # 1. 验证 Git 仓库
    repo_abs_path = validate_git_repo(repo_path)
    validate_branch_exists(repo_abs_path, source)
    validate_branch_exists(repo_abs_path, target)

    # 2. 获取变更文件
    file_statuses = get_diff_file_statuses(repo_abs_path, source, target)
    changed_files = filter_changed_files(file_statuses)
    absolute_paths = resolve_absolute_paths(repo_abs_path, changed_files)

    if not absolute_paths:
        return []

    # 3. 执行 P3C 检查
    json_contents = []
    for file_path in absolute_paths:
        print(f"  [扫描] {os.path.basename(file_path)} ...", file=sys.stderr)
        json_content = run_p3c_check(file_path)
        json_contents.append(json_content)

    # 4. 合并并过滤报告
    merged_data = merge_reports(json_contents)
    filtered_data = filter_by_priority(merged_data, max_priority)

    # 5. 转换输出格式
    return transform_to_output_format(filtered_data, repo_abs_path)


# ---------------------------------------------------------------------------
# CLI 接口
# ---------------------------------------------------------------------------

def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="Git 分支差异扫描 + P3C 代码审查",
    )
    parser.add_argument(
        "repo",
        help="Git 仓库根目录路径",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="源分支（feature 分支）",
    )
    parser.add_argument(
        "--target",
        default="origin/master",
        help="目标分支（默认 origin/master）",
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=2,
        choices=[1, 2, 3, 4, 5],
        help="最大优先级，默认 2（过滤掉 2 级以上的违规）",
    )
    return parser


def main() -> None:
    """主入口函数。"""
    parser = build_argument_parser()
    args = parser.parse_args()

    results = diff_scan(args.repo, args.source, args.target, args.priority)

    if not results:
        print("未发现违规项。")
        return

    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n总违规数：{len(results)}", file=sys.stderr)


if __name__ == "__main__":
    main()
