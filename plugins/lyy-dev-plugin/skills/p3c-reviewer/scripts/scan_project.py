"""全量扫描 Maven 项目的所有模块。

功能:
- 自动发现 Maven 多模块项目
- 逐模块扫描生成独立报告
- 支持优先级过滤（默认输出 1-2 级）
- 报告作为返回值，在控制台输出
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional

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

_MAX_POM_DEPTH = 10


class TargetType(Enum):
    SINGLE_FILE = auto()
    PROJECT_DIR = auto()
    SOURCE_DIR = auto()


@dataclass
class ScanTarget:
    module_name: str
    source_dir: str


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
    """执行 PMD 检查。

    Args:
        source_path: Java 源码目录或单个文件

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
# 模块名推断
# ---------------------------------------------------------------------------

def resolve_module_name(src_dir: str) -> str:
    """从源码路径向上回溯，取包含 pom.xml 的最近祖先目录名。

    如果找不到 pom.xml，则取 src 的上级目录名。

    Args:
        src_dir: 源码目录路径（通常是 .../module/src/main/java）

    Returns:
        推断的模块名
    """
    current = os.path.normpath(src_dir)
    for _ in range(5):
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
        if os.path.isfile(os.path.join(current, "pom.xml")):
            return os.path.basename(current)
    parts = os.path.normpath(src_dir).replace("\\", "/").split("/")
    try:
        idx = len(parts) - 1 - parts[::-1].index("src")
        return parts[idx - 1] if idx > 0 else parts[-1]
    except ValueError:
        return os.path.basename(os.path.dirname(src_dir))


# ---------------------------------------------------------------------------
# 模块自动发现
# ---------------------------------------------------------------------------

def parse_pom_modules(pom_path: str) -> List[str]:
    """解析 pom.xml 中的 <modules>/<module> 标签，兼容有/无命名空间。

    Args:
        pom_path: pom.xml 文件路径

    Returns:
        模块名列表
    """
    try:
        tree = ET.parse(pom_path)
    except ET.ParseError:
        return []
    root = tree.getroot()

    ns_match = re.match(r"\{(.+?)}", root.tag)
    ns = ns_match.group(1) if ns_match else ""

    modules: List[str] = []
    if ns:
        for mod_el in root.findall(f".//{{{ns}}}modules/{{{ns}}}module"):
            if mod_el.text and mod_el.text.strip():
                modules.append(mod_el.text.strip())
    else:
        for mod_el in root.findall(".//modules/module"):
            if mod_el.text and mod_el.text.strip():
                modules.append(mod_el.text.strip())
    return modules


def _discover_from_pom(
    project_dir: str, depth: int = 0, visited: Optional[set] = None
) -> List[ScanTarget]:
    """阶段 1：递归解析 pom.xml 发现模块。

    Args:
        project_dir: 项目根目录
        depth: 当前递归深度
        visited: 已访问的目录集合

    Returns:
        ScanTarget 列表
    """
    if depth > _MAX_POM_DEPTH:
        return []
    if visited is None:
        visited = set()

    project_dir = os.path.normpath(project_dir)
    if project_dir in visited:
        return []
    visited.add(project_dir)

    pom_path = os.path.join(project_dir, "pom.xml")
    if not os.path.isfile(pom_path):
        return []

    module_names = parse_pom_modules(pom_path)
    if not module_names:
        src_dir = os.path.join(project_dir, "src", "main", "java")
        if os.path.isdir(src_dir):
            return [ScanTarget(os.path.basename(project_dir), src_dir)]
        return []

    targets: List[ScanTarget] = []
    for mod_name in module_names:
        mod_dir = os.path.join(project_dir, mod_name)
        targets.extend(_discover_from_pom(mod_dir, depth + 1, visited))
    return targets


def _discover_by_convention(
    project_dir: str, known_dirs: set
) -> List[ScanTarget]:
    """阶段 2：兜底扫描——发现含 src/main/java 但未被 pom 覆盖的子目录。

    Args:
        project_dir: 项目根目录
        known_dirs: 已知的源码目录集合

    Returns:
        ScanTarget 列表
    """
    targets: List[ScanTarget] = []

    root_src = os.path.join(project_dir, "src", "main", "java")
    if os.path.isdir(root_src) and os.path.normpath(root_src) not in known_dirs:
        targets.append(ScanTarget(os.path.basename(project_dir), root_src))

    try:
        entries = os.listdir(project_dir)
    except OSError:
        return targets
    for entry in entries:
        child_dir = os.path.join(project_dir, entry)
        if not os.path.isdir(child_dir):
            continue
        src_dir = os.path.join(child_dir, "src", "main", "java")
        if os.path.isdir(src_dir) and os.path.normpath(src_dir) not in known_dirs:
            targets.append(ScanTarget(entry, src_dir))

    return targets


def discover_scan_targets(
    project_dir: str, *, no_recursive: bool = False
) -> List[ScanTarget]:
    """两阶段模块发现：pom 递归 + 兜底扫描。

    Args:
        project_dir: 项目根目录
        no_recursive: 是否禁用 pom 递归

    Returns:
        ScanTarget 列表
    """
    pom_targets: List[ScanTarget] = []
    if not no_recursive:
        pom_targets = _discover_from_pom(project_dir)

    known_dirs = {os.path.normpath(t.source_dir) for t in pom_targets}
    convention_targets = _discover_by_convention(project_dir, known_dirs)

    all_targets = pom_targets + convention_targets
    seen: set = set()
    unique: List[ScanTarget] = []
    for t in all_targets:
        key = os.path.normpath(t.source_dir)
        if key not in seen:
            seen.add(key)
            unique.append(t)
    unique.sort(key=lambda t: t.module_name)
    return unique


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

def scan_project(
    project_dir: str,
    max_priority: int = 3,
    no_recursive: bool = False
) -> Dict[str, Dict[str, Any]]:
    """扫描项目所有模块，返回 {模块名：过滤后的 JSON 报告}。

    Args:
        project_dir: 项目根目录
        max_priority: 最大优先级（默认 3，即保留 Blocker/Critical/Major 级违规）
        no_recursive: 是否禁用 pom 递归

    Returns:
        {模块名：过滤后的 JSON 报告对象} 字典
    """
    project_dir = os.path.abspath(project_dir)
    scan_targets = discover_scan_targets(project_dir, no_recursive=no_recursive)

    if not scan_targets:
        print("  [WARN] 未发现任何可扫描的模块", file=sys.stderr)
        return {}

    results: Dict[str, Dict[str, Any]] = {}

    for t in scan_targets:
        print(f"  [扫描] {t.module_name} ...")
        json_content = run_p3c_check(t.source_dir)
        try:
            data = json.loads(json_content)
            filtered_data = filter_by_priority(data, max_priority)
            results[t.module_name] = filtered_data
        except json.JSONDecodeError:
            print(f"  [ERROR] 解析 {t.module_name} 的 JSON 失败", file=sys.stderr)
            results[t.module_name] = {"files": []}

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="全量扫描 Maven 项目的所有模块",
    )
    parser.add_argument(
        "project",
        help="Maven 项目根目录",
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=3,
        choices=[1, 2, 3, 4, 5],
        help="最大优先级（默认 3，输出 Blocker/Critical/Major 级违规）",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="禁用 pom.xml 递归发现，仅兜底扫描",
    )
    parser.add_argument(
        "--list-modules",
        action="store_true",
        help="仅列出待扫描模块，不执行检查",
    )
    return parser


def main() -> None:
    """主入口函数。"""
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.list_modules:
        targets = discover_scan_targets(args.project, no_recursive=args.no_recursive)
        print(f"发现 {len(targets)} 个模块:")
        for t in targets:
            print(f"  {t.module_name} -> {t.source_dir}")
        return

    results = scan_project(args.project, args.priority, args.no_recursive)

    if not results:
        print("未发现任何可扫描的模块。")
        return

    print(json.dumps(results, indent=2, ensure_ascii=False))

    total_violations = sum(count_violations(data) for data in results.values())
    print(f"\n检查完成！总违规数：{total_violations}", file=sys.stderr)


if __name__ == "__main__":
    main()
