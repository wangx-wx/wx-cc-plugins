"""批量扫描多个文件，合并报告输出。

功能:
- 支持批量扫描多个文件
- 多个文件的报告合并为一个 JSON 输出
- 支持优先级过滤（默认输出 1-2 级）
- 报告作为返回值，在控制台输出
"""

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, List

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


# ---------------------------------------------------------------------------
# classpath
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
# PMD 执行
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

    import subprocess
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_str = proc.stdout.decode("utf-8", errors="replace")
    stderr_str = proc.stderr.decode("gbk", errors="replace")

    if stderr_str:
        for line in stderr_str.strip().splitlines()[:5]:
            print(f"  [WARN] {line}", file=sys.stderr)

    return stdout_str


# ---------------------------------------------------------------------------
# JSON 合并
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
            # PMD JSON 格式：{"files": [{"filename": "...", "violations": [...]}]}
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
# 优先级过滤
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

        # 过滤出符合优先级的违规
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
# 违规统计
# ---------------------------------------------------------------------------

def count_violations(data: Dict[str, Any]) -> int:
    """统计 JSON 报告中的违规项数量。

    Args:
        data: JSON 报告对象

    Returns:
        违规项数量
    """
    count = 0
    for file_entry in data.get("files", []):
        count += len(file_entry.get("violations", []))
    return count


# ---------------------------------------------------------------------------
# 入口函数
# ---------------------------------------------------------------------------

def batch_scan_files(
    file_paths: List[str], max_priority: int = 3
) -> Dict[str, Any]:
    """扫描多个文件，返回过滤后的合并 JSON 报告。

    Args:
        file_paths: 文件路径列表
        max_priority: 最大优先级（默认 3，即保留 Blocker/Critical/Major 级违规）

    Returns:
        过滤后的合并 JSON 报告对象
    """
    json_contents = []

    for file_path in file_paths:
        if not os.path.isfile(file_path):
            print(f"  [WARN] 文件不存在：{file_path}", file=sys.stderr)
            continue

        print(f"  [扫描] {os.path.basename(file_path)} ...")
        json_content = run_p3c_check(file_path)
        json_contents.append(json_content)

    merged_data = merge_reports(json_contents)
    filtered_data = filter_by_priority(merged_data, max_priority)

    return filtered_data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="批量扫描多个文件，合并报告输出",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="文件路径列表",
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=3,
        choices=[1, 2, 3, 4, 5],
        help="最大优先级（默认 3，输出 Blocker/Critical/Major 级违规）",
    )
    return parser


def main() -> None:
    """主入口函数。"""
    parser = build_argument_parser()
    args = parser.parse_args()

    result_data = batch_scan_files(args.files, args.priority)
    print(json.dumps(result_data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
