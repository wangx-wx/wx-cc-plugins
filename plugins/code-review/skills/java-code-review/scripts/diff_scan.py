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
import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SCRIPT_DIR, "lib")


def _decode_output(data: bytes) -> str:
    """解码子进程输出（stdout/stderr 通用）。

    Windows 下 Git/Java 的输出编码不确定，按优先级尝试：
    UTF-8 → GBK → 系统默认编码（带 replace）。
    """
    for encoding in ("utf-8", "gbk"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode(sys.getdefaultencoding(), errors="replace")

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
# 环境前置检查
# ---------------------------------------------------------------------------

def validate_java_available() -> None:
    """验证 Java 运行环境可用。

    Raises:
        SystemExit: java 未安装或不在 PATH 中
    """
    try:
        proc = subprocess.run(
            ["java", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise SystemExit("java -version 返回非零退出码，请检查 Java 安装")
    except FileNotFoundError:
        raise SystemExit("java 命令未找到，请确认已安装 JDK/JRE 并加入 PATH")


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
    proc = subprocess.run(
        ["git", "-C", abs_path, "rev-parse", "--git-dir"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise SystemExit(f"不是有效的 Git 仓库: {abs_path}")
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
        stderr_str = _decode_output(proc.stderr).strip()
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

    stderr_str = _decode_output(proc.stderr).strip()
    if proc.returncode != 0:
        raise SystemExit(f"git diff 执行失败:\n  {stderr_str}")
    if stderr_str:
        for line in stderr_str.splitlines()[:5]:
            logger.warning("git diff stderr: %s", line)

    stdout_str = _decode_output(proc.stdout)
    results: List[Tuple[str, str]] = []
    for line in stdout_str.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            # R(ename) / C(opy): status\told_path\tnew_path → 取新路径
            results.append((parts[0].strip(), parts[2].strip()))
        elif len(parts) == 2:
            results.append((parts[0].strip(), parts[1].strip()))
    return results


# ---------------------------------------------------------------------------
# 变更行范围提取
# ---------------------------------------------------------------------------

def get_changed_line_ranges(
    repo_path: str, source: str, target: str
) -> Dict[str, List[Tuple[int, int]]]:
    """获取每个变更文件的变更行范围（hunk 粒度）。

    使用 git diff -U0（零上下文）解析 hunk 头，提取新文件侧的行范围。

    Args:
        repo_path: 仓库绝对路径
        source: 源分支
        target: 目标分支

    Returns:
        {相对路径: [(start, end), ...]} 的字典，start/end 为闭区间行号
    """
    cmd = [
        "git", "-C", repo_path,
        "diff", "-U0", f"{target}...{source}",
    ]
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError:
        raise SystemExit("git 命令未找到，请确认已安装 Git 并加入 PATH")

    if proc.returncode != 0:
        stderr_str = _decode_output(proc.stderr).strip()
        raise SystemExit(f"git diff -U0 执行失败:\n  {stderr_str}")

    stdout_str = _decode_output(proc.stdout)
    changed_ranges: Dict[str, List[Tuple[int, int]]] = {}
    current_file = None

    for line in stdout_str.splitlines():
        # +++ b/path/to/file → 提取文件相对路径
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@") and current_file:
            # 解析 @@ -old +new_start,new_count @@ 中的 new 侧
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1
                if count > 0:  # count=0 表示纯删除，无新行
                    if current_file not in changed_ranges:
                        changed_ranges[current_file] = []
                    changed_ranges[current_file].append(
                        (start, start + count - 1)
                    )

    return changed_ranges


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


def is_test_file(path: str) -> bool:
    """判断文件是否为单元测试文件。

    匹配规则: 路径包含 src/test/（Maven/Gradle 标准测试目录）
    兼容单模块项目（路径以 src/test/ 开头）和多模块项目（路径包含 /src/test/）
    """
    normalized = path.replace("\\", "/")
    return "/src/test/" in normalized or normalized.startswith("src/test/")


def get_current_branch(repo_path: str) -> str:
    """获取仓库当前 checkout 的分支名。

    Returns:
        分支名，detached HEAD 时返回空字符串
    """
    cmd = ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"]
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError:
        return ""
    branch = _decode_output(proc.stdout).strip()
    return "" if branch == "HEAD" else branch


def resolve_working_tree_paths(
    repo_path: str, relative_paths: List[str]
) -> List[str]:
    """将相对路径转为工作区绝对路径，跳过不存在的文件。"""
    absolute_paths: List[str] = []
    for rel_path in relative_paths:
        abs_path = os.path.normpath(os.path.join(repo_path, rel_path))
        if os.path.isfile(abs_path):
            absolute_paths.append(abs_path)
        else:
            logger.warning("文件在工作区中不存在: %s", rel_path)
    return absolute_paths


def extract_files_from_branch(
    repo_path: str, branch: str, relative_paths: List[str], dest_dir: str
) -> List[str]:
    """通过 git show 从指定分支提取文件到临时目录。

    不依赖工作区状态，支持远程分支。

    Args:
        repo_path: 仓库绝对路径
        branch: 分支名（本地或远程均可）
        relative_paths: 相对于仓库根目录的文件路径列表
        dest_dir: 目标目录

    Returns:
        提取成功的文件绝对路径列表
    """
    extracted: List[str] = []
    for rel_path in relative_paths:
        dest_path = os.path.join(dest_dir, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        cmd = ["git", "-C", repo_path, "show", f"{branch}:{rel_path}"]
        try:
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except FileNotFoundError:
            raise SystemExit("git 命令未找到，请确认已安装 Git 并加入 PATH")

        if proc.returncode != 0:
            logger.warning("无法从分支 %s 提取文件: %s", branch, rel_path)
            continue

        with open(dest_path, "wb") as f:
            f.write(proc.stdout)
        extracted.append(dest_path)

    return extracted


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

def run_p3c_check(source_paths: List[str], classpath: str) -> str:
    """对一组文件执行 PMD 检查。

    PMD 的 -d 参数支持逗号分隔的多路径，一次 JVM 启动完成全部扫描。

    Args:
        source_paths: 文件路径列表
        classpath: 预构建的 classpath 字符串

    Returns:
        JSON 格式的检查报告字符串

    Raises:
        SystemExit: PMD 执行出现非预期错误
    """
    cmd = [
        "java",
        "-Dfile.encoding=UTF-8",
        "-cp", classpath,
        "net.sourceforge.pmd.PMD",
        "-d", ",".join(source_paths),
        "-R", ",".join(P3C_RULESETS),
        "-f", "json",
        "--encoding", "UTF-8",
    ]

    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout_str = _decode_output(proc.stdout)
    stderr_str = _decode_output(proc.stderr)

    if stderr_str:
        for line in stderr_str.strip().splitlines()[:5]:
            logger.warning("PMD stderr: %s", line)

    # PMD 退出码约定: 0=无违规, 4=有违规, 其他=执行错误
    if proc.returncode not in (0, 4):
        raise SystemExit(
            f"PMD 执行失败 (exit code {proc.returncode}):\n  {stderr_str[:500]}"
        )

    return stdout_str


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
# 变更行过滤
# ---------------------------------------------------------------------------

def filter_by_changed_lines(
    results: List[Dict[str, Any]],
    changed_ranges: Dict[str, List[Tuple[int, int]]],
) -> List[Dict[str, Any]]:
    """只保留起始行落在变更 hunk 范围内的违规项。

    判断逻辑：违规的 beginline 落在任一 hunk 的 [start, end] 内即保留，
    确保只输出由本次变更引入的违规。

    Args:
        results: 转换后的违规项列表
        changed_ranges: {文件相对路径: [(start, end), ...]}

    Returns:
        过滤后的违规项列表
    """
    filtered: List[Dict[str, Any]] = []

    for item in results:
        file_name = item["fileName"].replace("\\", "/")
        ranges = changed_ranges.get(file_name)
        if ranges is None:
            continue

        begin = item.get("beginline", 0)

        # 只检查违规起始行是否落在变更 hunk 内
        for r_start, r_end in ranges:
            if r_start <= begin <= r_end:
                filtered.append(item)
                break

    return filtered


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

    通过 git show 将 source 分支的变更文件提取到临时目录进行扫描，
    不依赖工作区状态，支持远程分支。

    Args:
        repo_path: Git 仓库路径
        source: 源分支（本地或远程均可）
        target: 目标分支
        max_priority: 最大优先级（过滤阈值）

    Returns:
        简化格式的违规项列表
    """
    # 1. 环境与仓库验证
    validate_java_available()
    repo_abs_path = validate_git_repo(repo_path)
    validate_branch_exists(repo_abs_path, source)
    validate_branch_exists(repo_abs_path, target)

    # 2. 获取变更文件与变更行范围
    file_statuses = get_diff_file_statuses(repo_abs_path, source, target)
    changed_ranges = get_changed_line_ranges(repo_abs_path, source, target)
    changed_files = filter_changed_files(file_statuses)
    changed_files = [
        f for f in changed_files
        if f.endswith(".java") and not is_test_file(f)
    ]

    if not changed_files:
        return []

    # 3. 获取文件并扫描
    classpath = build_classpath()
    current_branch = get_current_branch(repo_abs_path)
    use_worktree = (current_branch == source)

    if use_worktree:
        # source 就是当前分支，直接读工作区文件
        absolute_paths = resolve_working_tree_paths(repo_abs_path, changed_files)
        if not absolute_paths:
            return []
        logger.info("共 %d 个文件待扫描（工作区）", len(absolute_paths))
        json_content = run_p3c_check(absolute_paths, classpath)
        base_path = repo_abs_path
    else:
        # source 非当前分支，提取到临时目录
        with tempfile.TemporaryDirectory(prefix="p3c_scan_") as tmp_dir:
            absolute_paths = extract_files_from_branch(
                repo_abs_path, source, changed_files, tmp_dir
            )
            if not absolute_paths:
                return []
            logger.info("共 %d 个文件待扫描（临时目录）", len(absolute_paths))
            json_content = run_p3c_check(absolute_paths, classpath)
            base_path = tmp_dir

    # 4. 解析并过滤报告
    try:
        report_data = json.loads(json_content) if json_content.strip() else {"files": []}
    except json.JSONDecodeError:
        logger.warning("PMD 输出无法解析为 JSON")
        report_data = {"files": []}

    filtered_data = filter_by_priority(report_data, max_priority)

    # 5. 转换输出格式并过滤到变更行范围
    results = transform_to_output_format(filtered_data, base_path)
    return filter_by_changed_lines(results, changed_ranges)


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
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="输出 DEBUG 级别日志（默认 INFO）",
    )
    return parser


def main() -> None:
    """主入口函数。"""
    parser = build_argument_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    results = diff_scan(args.repo, args.source, args.target, args.priority)

    if not results:
        print("未发现违规项。")
        return

    print(json.dumps(results, indent=2, ensure_ascii=False))
    logger.info("总违规数：%d", len(results))


if __name__ == "__main__":
    main()
