#!/usr/bin/env python3
"""Safely normalize Sanger 16S filenames to ID_27F/1492R.ext.

Preview: python3 rename_16s.py PATH
Apply:   python3 rename_16s.py PATH --apply
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# Supported example patterns:
# (18)_[1492R]_32226093000425_0027.ab1 -> 18_1492R.ab1
# N6_32226093000417_(6)_[27F].ab1 -> 6_27F.ab1
# 6_27F.ab1 -> no change
PATTERNS = [
    re.compile(r"^\((?P<id>[A-Za-z0-9-]+)\)_\[(?P<primer>27F|1492R)\](?:_.+)?$", re.I),
    re.compile(r"^.+_\((?P<id>[A-Za-z0-9-]+)\)_\[(?P<primer>27F|1492R)\]$", re.I),
    re.compile(r"^(?P<id>[A-Za-z0-9-]+)_(?P<primer>27F|1492R)$", re.I),
]
EXTENSIONS = {".ab1", ".seq", ".fasta", ".fa", ".fas"}


def new_name(path):
    extension = path.suffix.lower()
    if extension not in EXTENSIONS:
        return None
    for pattern in PATTERNS:
        match = pattern.fullmatch(path.stem)
        if match:
            return f"{match.group('id')}_{match.group('primer').upper()}{extension}"
    return None


def main():
    parser = argparse.ArgumentParser(description="批量改成 ID_27F.ab1 / ID_1492R.seq 等格式，默认只预览。")
    parser.add_argument("folder", type=Path, help="包含测序文件的文件夹（仅处理本层文件）")
    parser.add_argument("--apply", action="store_true", help="确认执行重命名；不加此参数仅预览")
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        parser.error(f"文件夹不存在：{folder}")

    changes = []
    unrecognized = []
    unchanged = 0
    for source in sorted(folder.iterdir(), key=lambda p: p.name):
        if not source.is_file() or source.suffix.lower() not in EXTENSIONS:
            continue
        filename = new_name(source)
        if filename is None:
            unrecognized.append(source.name)
        elif source.name == filename:
            unchanged += 1
        else:
            changes.append((source, folder / filename))

    # Never overwrite an existing file; reject the entire batch if a name is ambiguous.
    target_groups = defaultdict(list)
    for source, target in changes:
        target_groups[target.name.casefold()].append(source.name)
    problems = []
    for source, target in changes:
        if target.exists():
            problems.append(f"目标已存在：{target.name} （源：{source.name}）")
    for dest, sources in target_groups.items():
        if len(sources) > 1:
            problems.append(f"多个源文件要改成同名文件 {dest}：{', '.join(sources)}")

    print(f"文件夹：{folder}")
    print(f"准备改名：{len(changes)}，已符合格式：{unchanged}，未识别：{len(unrecognized)}")
    for source, target in changes:
        print(f"  {source.name}  ->  {target.name}")
    if unrecognized:
        print("\n未识别的测序文件（保持原样）：")
        for filename in unrecognized:
            print(f"  {filename}")
    if problems:
        print("\n发现同名冲突，未修改任何文件：", file=sys.stderr)
        for problem in sorted(set(problems)):
            print(f"  {problem}", file=sys.stderr)
        return 2
    if not args.apply:
        print("\n当前是预览模式，未修改任何文件。确认后在命令末尾添加 --apply 执行。")
        return 0
    for source, target in changes:
        source.rename(target)
    print(f"\n已改名 {len(changes)} 个文件；原始数据内容未改变。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
