"""通用 Git Diff 包装脚本

执行 git diff {target}...{source} -- <pathspecs>，输出原始 diff 结果。
供 Java Code Review Skill 的 Agent 2/3/4 统一调用。

用法:
    python git_diff.py <repo> --source <branch> --target <branch> [-- pathspec ...]

示例:
    # Agent 2: Java 文件（排除测试）
    python git_diff.py /repo --source feat/x --target origin/master -- "*.java" ":(exclude)*/src/test/*"

    # Agent 3: 配置文件（排除 java/xml/md）
    python git_diff.py /repo --source feat/x --target origin/master -- ":(exclude)*.java" ":(exclude)*.xml" ":(exclude)*.md"

    # Agent 4: XML 文件（排除 pom.xml）
    python git_diff.py /repo --source feat/x --target origin/master -- "*.xml" ":(exclude)*pom.xml"

    # 无 pathspec，获取全部变更
    python git_diff.py /repo --source feat/x --target origin/master
"""

import argparse
import os
import subprocess
import sys


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "gbk"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode(sys.getdefaultencoding(), errors="replace")


def _validate_repo(path: str) -> str:
    abs_path = os.path.abspath(path)
    if not os.path.isdir(abs_path):
        raise SystemExit(f"路径不存在或不是目录: {abs_path}")
    if not os.path.exists(os.path.join(abs_path, ".git")):
        raise SystemExit(f"不是有效的 Git 仓库: {abs_path}")
    return abs_path


def _validate_branch(repo: str, branch: str) -> None:
    proc = subprocess.run(
        ["git", "-C", repo, "rev-parse", "--verify", branch],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise SystemExit(f"分支不存在: {branch}\n  {_decode(proc.stderr).strip()}")


def git_diff(repo: str, source: str, target: str, pathspecs: list) -> str:
    """执行 git diff {target}...{source} -- [pathspecs] 并返回原始输出。"""
    cmd = ["git", "-C", repo, "diff", f"{target}...{source}"]
    if pathspecs:
        cmd.append("--")
        cmd.extend(pathspecs)

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        stderr = _decode(proc.stderr).strip()
        raise SystemExit(f"git diff 执行失败:\n  {stderr}")
    return _decode(proc.stdout)


def main() -> None:
    # 手动分割 -- 前后的参数，-- 后的部分作为 pathspec
    argv = sys.argv[1:]
    if "--" in argv:
        idx = argv.index("--")
        script_args = argv[:idx]
        pathspecs = argv[idx + 1:]
    else:
        script_args = argv
        pathspecs = []

    parser = argparse.ArgumentParser(description="通用 Git Diff 包装脚本")
    parser.add_argument("repo", help="Git 仓库路径")
    parser.add_argument("--source", required=True, help="源分支")
    parser.add_argument("--target", default="origin/master", help="目标分支（默认 origin/master）")
    args = parser.parse_args(script_args)

    repo = _validate_repo(args.repo)
    _validate_branch(repo, args.source)
    _validate_branch(repo, args.target)

    output = git_diff(repo, args.source, args.target, pathspecs)
    if output:
        print(output, end="")
    else:
        print("无变更内容。", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
