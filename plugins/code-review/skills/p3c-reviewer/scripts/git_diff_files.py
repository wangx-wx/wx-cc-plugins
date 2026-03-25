"""获取 Git 仓库中两个分支之间变更的文件绝对路径。

功能:
- 对比 source 分支相对 target 分支引入的变更
- 输出所有非删除状态的变更文件
- 支持 lines / args / json 三种输出格式
- 可配合 batch_scan_files.py 做增量代码检查
"""

import argparse
import json
import os
import subprocess
import sys
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Git 仓库验证
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
# Git diff 执行
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
# 文件过滤与路径解析
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
# 输出格式化
# ---------------------------------------------------------------------------

def format_output(file_paths: List[str], output_format: str) -> str:
    """按指定格式输出文件路径列表。

    Args:
        file_paths: 绝对路径列表
        output_format: lines / args / json

    Returns:
        格式化后的字符串
    """
    if output_format == "json":
        return json.dumps(file_paths, ensure_ascii=False, indent=2)
    if output_format == "args":
        return " ".join(file_paths)
    # lines（默认）
    return "\n".join(file_paths)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="获取 Git 两个分支之间变更的文件路径，用于增量代码检查",
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
        "--output-format",
        choices=["lines", "args", "json"],
        default="lines",
        help="输出格式（默认 lines：每行一个路径）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示将要执行的 git 命令，不实际执行",
    )
    return parser


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    """顶层编排。"""
    parser = build_argument_parser()
    args = parser.parse_args()

    repo_path = validate_git_repo(args.repo)

    if args.dry_run:
        cmd = f"git -C {repo_path} diff --name-status {args.target}...{args.source}"
        print(f"[DRY-RUN] {cmd}")
        return

    validate_branch_exists(repo_path, args.source)
    validate_branch_exists(repo_path, args.target)

    file_statuses = get_diff_file_statuses(repo_path, args.source, args.target)
    changed_files = filter_changed_files(file_statuses)

    if not changed_files:
        print("[INFO] 未发现变更文件", file=sys.stderr)
        return

    absolute_paths = resolve_absolute_paths(repo_path, changed_files)

    if not absolute_paths:
        print("[INFO] 变更文件均不存在于当前工作区", file=sys.stderr)
        return

    output = format_output(absolute_paths, args.output_format)
    print(output)


if __name__ == "__main__":
    main()
