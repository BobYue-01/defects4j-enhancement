import os
import re
import argparse
from typing import Dict, List, Tuple
import logging


# 一条作用域信息：名称，类型，起始行，结束行
Scope = Tuple[str, str, int, int]

# 用于匹配类、方法、构造器的简单正则（可根据具体语言调整）
CLASS_RE       = re.compile(r'^\s*(public|protected|private)?\s*class\s+(\w+)')
METHOD_RE      = re.compile(r'^\s*(public|protected|private)?\s*(static\s+)?\w+\s+(\w+)\s*\(.*\)\s*\{')
CONSTRUCTOR_RE = re.compile(r'^\s*(public|protected|private)?\s+(\w+)\s*\(.*\)\s*\{')

CONTROL_KW = {'if', 'for', 'while', 'switch', 'catch', 'try'}

HUNK_HEADER = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def parse_scopes(lines: List[str]) -> List[Scope]:
    """
    扫描文件所有行，返回所有 class/constructor/method 作用域：
    [(name, kind, start_line, end_line), …]
    """
    scopes: List[Scope] = []
    stack: List[Dict] = []  # 用来追踪嵌套的大括号和对应的作用域

    for lineno, line in enumerate(lines, start=1):
        # 检测新的作用域开始
        m_cls = CLASS_RE.match(line)
        m_ctor = CONSTRUCTOR_RE.match(line)
        m_mth = METHOD_RE.match(line)
        kind = name = None

        if m_cls:
            kind, name = "class", m_cls.group(2)
        elif m_ctor:
            kind, name = "ctor", m_ctor.group(2)
        elif m_mth:
            kind, name = "method", m_mth.group(3)

        if name in CONTROL_KW:
            # 控制语句（如 if/for/while/switch/catch/try）不算作用域
            kind = None

        # 如果是新的作用域，压入栈
        if kind:
            stack.append({
                "kind": kind,
                "name": name,
                "start": lineno,
                "brace_level": line.count('{') - line.count('}')
            })
            continue

        # 对所有未闭合的作用域，调整它们的 brace_level
        for scope in stack:
            scope["brace_level"] += line.count('{') - line.count('}')

        # 检测栈顶作用域是否已闭合（brace_level 回到 0）
        while stack and stack[-1]["brace_level"] == 0:
            s = stack.pop()
            scopes.append((s["name"], s["kind"], s["start"], lineno))

    return scopes


def minimal_covering_scopes(
    scopes: List[Scope],
    hunks: List[Tuple[int, int]]
) -> List[Scope]:
    """
    给定所有 scopes 和 hunks[(start,end),…]（基于旧文件行号），
    返回最小的不重叠作用域集合，覆盖所有改动行。
    """
    # 先为每一个改动行定位它所在的最小作用域
    line_to_scope: Dict[int, Scope] = {}
    for name, kind, s, e in scopes:
        for ln in range(s, e+1):
            # 只在第一次（最内层）记录
            if ln not in line_to_scope:
                line_to_scope[ln] = (name, kind, s, e)

    # 收集所有改动行对应的作用域
    selected: List[Scope] = []
    for hstart, hend in hunks:
        for ln in range(hstart, hend+1):
            if ln in line_to_scope:
                selected.append(line_to_scope[ln])

    # 合并：按 (name,kind,start,end) 唯一，并按起始行排序
    merged: Dict[Tuple, Scope] = {}
    for sc in selected:
        key = (sc[0], sc[1], sc[2], sc[3])
        merged[key] = sc

    # 输出一个有序列表
    return sorted(merged.values(), key=lambda t: t[2])


def parse_patch_hunks(patch_path: str) -> List[Tuple[str, int, int]]:
    """
    解析一个 git patch 文件，返回所有 hunk 中真正的改动行在 patch 文件中的行号范围：
    [(file_path, first_changed_line_no, last_changed_line_no), …]
    """
    hunks = []
    with open(patch_path, encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        # 1) diff --git 更新文件路径，跳过接下来的 ---/+++ 行
        if line.startswith('diff --git'):
            parts = line.strip().split()
            current_file = parts[2][2:]  # 把 "a/foo.py" → "foo.py"
            i += 1
            # 跳过 --- a/... 和 +++ b/...
            if i < len(lines) and lines[i].startswith('index '): i += 1
            if i < len(lines) and lines[i].startswith('--- '): i += 1
            if i < len(lines) and lines[i].startswith('+++ '): i += 1
            continue

        # 2) 匹配 hunk header，初始化计数器
        m = HUNK_HEADER.match(line)
        if m:
            old_start = int(m.group(1))
            old_count = int(m.group(2) or 1)
            new_start = int(m.group(3))
            new_count = int(m.group(4) or 1)

            # 游标从 header 里的起始行号开始
            cur_old = old_start
            cur_new = new_start

            # 用来收集所有改动行在 old/new 文件里的行号
            old_changed: List[int] = []
            new_changed: List[int] = []

            j = i + 1
            while cur_old < old_start + old_count or cur_new < new_start + new_count:
                ln = lines[j]
                if ln.startswith('diff --git') or ln.startswith('@@ '):
                    break
                j += 1

                if ln.startswith(' '):
                    # 上下文行：old/new 游标都 +1
                    cur_old += 1
                    cur_new += 1

                elif ln.startswith('-'):
                    # 删除行：记录 old/new；old 游标 +1；new 游标不动
                    old_changed.append(cur_old)
                    new_changed.append(cur_new)
                    cur_old += 1

                elif ln.startswith('+'):
                    # 新增行：记录 old/new；old 游标不动；new 游标 +1
                    old_changed.append(cur_old)
                    new_changed.append(cur_new)
                    cur_new += 1

                else:
                    # 其它，中断
                    break

            # 如果本 hunk 有改动，再把最小/最大行号入结果
            if new_changed:
                first_new = min(new_changed)
                last_new  = max(new_changed)
                hunks.append((current_file, first_new, last_new))

            # 跳过 body
            i = j
            continue

        i += 1

    return hunks


def locate_by_patch(diff_file: str, src_root: str) -> List[Tuple[str, List[Scope]]]:
    """
    根据 diff 文件和源代码根目录，返回每个文件及其改动行的最小覆盖作用域。
    """
    logger = logging.getLogger(__name__)
    hunks = parse_patch_hunks(diff_file)
    result = {}

    for hunk in hunks:
        rel_file_path = hunk[0]
        abs_file_path = os.path.join(src_root, rel_file_path)
        start_line = hunk[1]
        end_line = hunk[2]

        # 读取源文件
        if not os.path.exists(abs_file_path):
            logger.warning(f"文件不存在：{abs_file_path}")
            continue
        with open(abs_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 提取作用域
        scopes = parse_scopes(lines)

        # 找到最小覆盖作用域
        covering_scopes = minimal_covering_scopes(scopes, [(start_line, end_line)])
        if rel_file_path not in result:
            result[rel_file_path] = []
        result[rel_file_path].extend(covering_scopes)

    for rel_file_path, scopes in result.items():
        # 去重
        merged: Dict[Tuple, Scope] = {}
        for sc in scopes:
            key = (sc[0], sc[1], sc[2], sc[3])
            merged[key] = sc
        # 输出一个有序列表
        result[rel_file_path] = sorted(merged.values(), key=lambda t: t[2])

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract modified code scopes from diff')
    parser.add_argument('--diff_file', help='Path to unified diff file')
    parser.add_argument('--src_root', help='Root directory of source files')
    args = parser.parse_args()

    results = locate_by_patch(args.diff_file, args.src_root)
    for file_path, scopes in results.items():
        print(f"File: {file_path}")
        for scope in scopes:
            print(f"  {scope}")
