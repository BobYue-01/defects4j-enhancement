import os
import logging
import subprocess
from checkout_version import checkout_version, clear_temp_dir
from extract_readme import extract_readme
from locate_oracle import locate_oracle


PATCH_EXAMPLE = """--- a/file.py
+++ b/file.py
@@ -1,27 +1,35 @@
 def euclidean(a, b):
-    while b:
-        a, b = b, a % b
-    return a
+    if b == 0:
+        return a
+    return euclidean(b, a % b)
 
 
 def bresenham(x0, y0, x1, y1):
     points = []
     dx = abs(x1 - x0)
     dy = abs(y1 - y0)
-    sx = 1 if x0 < x1 else -1
-    sy = 1 if y0 < y1 else -1
-    err = dx - dy
+    x, y = x0, y0
+    sx = -1 if x0 > x1 else 1
+    sy = -1 if y0 > y1 else 1
 
-    while True:
-        points.append((x0, y0))
-        if x0 == x1 and y0 == y1:
-            break
-        e2 = 2 * err
-        if e2 > -dy:
+    if dx > dy:
+        err = dx / 2.0
+        while x != x1:
+            points.append((x, y))
             err -= dy
-            x0 += sx
-        if e2 < dx:
-            err += dx
-            y0 += sy
+            if err < 0:
+                y += sy
+                err += dx
+            x += sx
+    else:
+        err = dy / 2.0
+        while y != y1:
+            points.append((x, y))
+            err -= dx
+            if err < 0:
+                x += sx
+                err += dy
+            y += sy
 
+    points.append((x, y))
     return points"""


def add_lines_list(content):
    content_with_lines = list()
    for ix, line in enumerate(content.split("\n"), start=1):
        content_with_lines.append(f"{ix} {line}")
    return content_with_lines


def add_lines(content):
    return "\n".join(add_lines_list(content))


def make_code_text(files_dict, add_line_numbers=True):
    all_text = ""
    for filename, contents in sorted(files_dict.items()):
        all_text += f"[start of {filename}]\n"
        if add_line_numbers:
            all_text += add_lines(contents)
        else:
            all_text += contents
        all_text += f"\n[end of {filename}]\n"
    return all_text.strip("\n")


def prompt_style_2(instance):
    premise = "You will be provided with a partial code base and an issue statement explaining a problem to resolve."
    readmes_text = make_code_text(instance["readmes"]) if instance["readmes"] else ""
    code_text = make_code_text(instance["file_contents"])
    instructions = (
        "I need you to solve this issue by generating a single patch file that I can apply "
        + "directly to this repository using git apply. Please respond with a single patch "
        + "file in the following format."
    )
    problem_statement = instance["problem_statement"]
    final_text = [
        premise,
        "<issue>",
        problem_statement,
        "</issue>",
        "<code>",
        readmes_text,
        code_text,
        "</code>",
        instructions,
        "<patch>",
        PATCH_EXAMPLE,
        "</patch>",
    ]
    final_text = "\n".join(final_text)
    return final_text


def get_file_contents(file_path, logger):
    """
    获取文件内容，如果文件不存在，返回空值
    """
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return file.read()
    else:
        logger.warning(f"文件不存在：{file_path}")
        return ""


def process_instance(instance, method="oracle", clear=False):
    """
    处理指定的项目和缺陷版本，检出代码并提取 POM 描述和 Oracle 文件。
    """
    logger = logging.getLogger(__name__)

    # 检出指定版本
    project_id = instance["proj"]
    bug_id = instance["id"]
    checkout_dir = checkout_version(project_id, bug_id, version_suffix="b")
    if not checkout_dir:
        logger.error(f"检出失败：{project_id} {bug_id}")
        return None

    instance["problem_statement"] = "\n".join([
        instance["title"], instance["description"]
    ])

    # 提取 README 文件
    _ = extract_readme(checkout_dir)
    if _:
        readme_file, readme_content = _
        instance["readmes"] = {readme_file: readme_content}
    else:
        instance["readmes"] = {}
        logger.warning(f"README 文件不存在")

    if method == "oracle":
        # 提取 Oracle 文件
        files = locate_oracle(instance["classes_modified"])
        relative_dir = subprocess.run(
            f'defects4j export -p "dir.src.classes" -w {checkout_dir}',
            shell=True,
            capture_output=True
        ).stdout.decode().splitlines()[-1].strip()

        try:
            instance["file_contents"] = {
                file: get_file_contents(
                    os.path.join(checkout_dir, relative_dir, file), logger
                ) for file in files
            }
        except Exception as e:
            logger.error(f"文件路径错误：{e}")
            return None

    if clear:
        clear_temp_dir()

    return prompt_style_2(instance)


if __name__ == "__main__":
    # 示例数据
    instance = {
        "proj": "Closure",
        "id": 169,
        "classes_modified": "com.google.javascript.rhino.jstype.ArrowType;com.google.javascript.rhino.jstype.EquivalenceMethod;com.google.javascript.rhino.jstype.FunctionType;com.google.javascript.rhino.jstype.JSType;com.google.javascript.rhino.jstype.RecordType;com.google.javascript.rhino.jstype.UnionType",
        "url": "https://storage.googleapis.com/google-code-archive/v2/code.google.com/closure-compiler/issues/issue-791.json",
        "title": "Strange \"wrong parameter\" warning for callback function",
        "description": "<b>What steps will reproduce the problem?</b>\nCompile the followed code:\n   /** @param {{func: function()}} obj */\n   function test1(obj) {};\n   var fnStruc1 = {};\n   fnStruc1.func = function() {};\n   test1(fnStruc1); \n\n<b>What is the expected output? What do you see instead?</b>\nExpected: compiled OK\nI see:\nWARNING - actual parameter 1 of func does not match formal parameter\nfound   : {func: function (): undefined}\nrequired: {func: function (): ?}\nfunc(fnStruc);\n     ^\n\n<b>What version of the product are you using? On what operating system?</b>\nr2102, Win7 x64\n\n<b>Please provide any additional information below.</b>\nThe followed code compiles OK:\n   /** @param {{func: function()}} obj */\n   function test2(obj) {};\n   var fnStruc2 = { func: function() {} };\n   test2(fnStruc2);\n\nDiscussion: https://groups.google.com/d/topic/closure-compiler-discuss/JuzERhGo48I/discussion"
    }

    # 处理实例
    result = process_instance(instance, method="oracle")
    print(result)
