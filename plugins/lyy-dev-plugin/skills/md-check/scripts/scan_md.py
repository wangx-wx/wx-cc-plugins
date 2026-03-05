#!/usr/bin/env python3
"""
Markdown Content Scanner
扫描 Markdown 文件，统计指定标题等级下的内容字符数量。
支持在标题前后插入分隔符并输出到新目录。
"""

import argparse
import json
import os
import re
import sys


def parse_heading_level(line):
    """解析一行文本的标题等级，返回 (等级, 标题文本) 或 None"""
    match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
    if match:
        return len(match.group(1)), match.group(2).strip()
    return None


def scan_file(filepath, target_level):
    """
    扫描单个 md 文件，提取指定标题等级下的内容字符数。

    统计范围：从当前标题到下一个同级或更高级标题之间的文本，
    不包含子标题行及其下属内容。
    """
    results = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (UnicodeDecodeError, OSError):
        return results

    current_heading = None
    current_chars = 0
    current_start_line = -1
    in_sub_heading = False

    for i, line in enumerate(lines):
        parsed = parse_heading_level(line)

        if parsed:
            level, text = parsed

            if level == target_level:
                # 遇到同级标题，保存上一个标题的结果
                if current_heading is not None:
                    results.append({
                        'file': filepath,
                        'heading': current_heading,
                        'chars': current_chars,
                        'start_line': current_start_line,
                    })
                # 开始新的标题段落
                current_heading = text
                current_chars = 0
                current_start_line = i
                in_sub_heading = False

            elif level < target_level:
                # 遇到更高级标题，结束当前标题段落
                if current_heading is not None:
                    results.append({
                        'file': filepath,
                        'heading': current_heading,
                        'chars': current_chars,
                        'start_line': current_start_line,
                    })
                    current_heading = None
                    current_chars = 0
                in_sub_heading = False

            elif level > target_level and current_heading is not None:
                # 遇到子标题，标记进入子标题区域（不计入字符数）
                in_sub_heading = True

        else:
            # 普通文本行
            if current_heading is not None and not in_sub_heading:
                stripped = line.strip()
                if stripped:
                    current_chars += len(stripped)

    # 文件结束，保存最后一个标题的结果
    if current_heading is not None:
        results.append({
            'file': filepath,
            'heading': current_heading,
            'chars': current_chars,
            'start_line': current_start_line,
        })

    return results


def scan_directory(directory, target_level, recursive=True):
    """扫描目录下所有 md 文件"""
    all_results = []

    if recursive:
        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录和常见的非内容目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', '_separated')]
            for fname in files:
                if fname.lower().endswith('.md'):
                    filepath = os.path.join(root, fname)
                    all_results.extend(scan_file(filepath, target_level))
    else:
        for fname in os.listdir(directory):
            if fname.lower().endswith('.md'):
                filepath = os.path.join(directory, fname)
                if os.path.isfile(filepath):
                    all_results.extend(scan_file(filepath, target_level))

    # 按字符数降序排列
    all_results.sort(key=lambda x: x['chars'], reverse=True)
    return all_results


def insert_separators(directory, target_level, output_dir):
    """
    在指定标题等级的标题前后插入分隔符，输出到新目录。
    不修改源文件。
    """
    separator = '\n======\n'
    processed_files = 0

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', '_separated')]
        for fname in files:
            if not fname.lower().endswith('.md'):
                continue

            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, directory)
            out_path = os.path.join(output_dir, rel_path)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except (UnicodeDecodeError, OSError):
                continue

            new_lines = []
            in_target_section = False

            for line in lines:
                parsed = parse_heading_level(line)

                if parsed:
                    level, _ = parsed

                    if level == target_level:
                        if in_target_section:
                            # 上一段落结束 + 新段落开始，共用一个分隔符（避免重复）
                            new_lines.append(separator + '\n')
                        else:
                            # 首次进入目标段落，在标题前插入分隔符
                            new_lines.append(separator + '\n')
                        new_lines.append(line)
                        in_target_section = True

                    elif level < target_level:
                        # 遇到更高级标题，结束当前段落
                        if in_target_section:
                            new_lines.append(separator + '\n')
                            in_target_section = False
                        new_lines.append(line)

                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            # 文件结束，如果仍在目标段落中，插入结尾分隔符
            if in_target_section:
                new_lines.append(separator + '\n')

            # 写入输出文件
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            processed_files += 1

    return processed_files


def main():
    # Windows 环境下确保 stdout 使用 UTF-8
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description='Markdown Content Scanner')
    parser.add_argument('--dir', required=True, help='要扫描的目录路径')
    parser.add_argument('--level', type=int, default=2, choices=range(1, 7),
                        help='标题等级 (1-6)，默认 2 即 ##')
    parser.add_argument('--top', type=int, default=10, help='显示前 N 个结果')
    parser.add_argument('--recursive', action='store_true', default=True,
                        help='递归扫描子目录（默认开启）')
    parser.add_argument('--no-recursive', dest='recursive', action='store_false',
                        help='不递归扫描子目录')
    parser.add_argument('--insert-separator', action='store_true',
                        help='在标题前后插入分隔符')
    parser.add_argument('--output-dir', default=None,
                        help='分隔符输出目录（默认: <dir>/_separated）')

    args = parser.parse_args()

    directory = os.path.abspath(args.dir)
    if not os.path.isdir(directory):
        print(json.dumps({'error': f'目录不存在: {directory}'}), file=sys.stderr)
        sys.exit(1)

    if args.insert_separator:
        output_dir = args.output_dir or os.path.join(directory, '_separated')
        count = insert_separators(directory, args.level, output_dir)
        result = {
            'action': 'insert_separator',
            'output_dir': output_dir,
            'processed_files': count,
            'heading_level': args.level,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        all_results = scan_directory(directory, args.level, args.recursive)
        top_results = all_results[:args.top]

        # 将文件路径转为相对路径以便展示
        for r in top_results:
            r['file'] = os.path.relpath(r['file'], directory)

        output = {
            'action': 'scan',
            'directory': directory,
            'heading_level': args.level,
            'total_headings': len(all_results),
            'showing_top': min(args.top, len(all_results)),
            'results': top_results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
