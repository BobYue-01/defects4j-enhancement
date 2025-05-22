import os
import json
import subprocess
import argparse
import shutil
import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from checkout_version import TEMP_DIR, checkout_version
from locate_oracle_scope import locate_by_patch

TIMEOUT = 60 * 5  # 5 minutes

output_data = []
executor = ThreadPoolExecutor(max_workers=1)


def extract_hunks(patch_text):
    """
    Extract replacements per hunk from <patch> tags in non-patch format.
    Returns list of (filename, hunk_idx, replacement_text).
    """
    content = patch_text
    # strip surrounding <patch> tags
    m = re.search(r"<patch>(.*)</patch>", content, re.DOTALL)
    if m:
        content = m.group(1)
    # Remove leading and trailing <patch> tags
    patch_text = re.sub(r"^<patch>|</patch>$", "", patch_text)
    # Remove leading and trailing whitespace
    patch_text = patch_text.strip()
    hunks = []
    # pattern for each file
    file_sections = re.split(r"\[start of ([^\]]+)\]", content)
    # first element before first [start of ..] is empty or prefix
    for i in range(1, len(file_sections), 2):
        filename = file_sections[i].strip()
        body = file_sections[i+1]
        # find each hunk
        for h in re.finditer(r"\{hunk (\d+)\}(.*?)\{/hunk \1\}", body, re.DOTALL):
            idx = int(h.group(1))
            repl = h.group(2).lstrip("\n")  # remove leading newline
            hunks.append((filename, idx, repl))
    return hunks


def apply_replacements(data, pred, logger):
    pid = data.get("proj")
    bid = str(data.get("id"))
    patch_text = pred.get("predict", "")
    if not (pid and bid and patch_text):
        logger.info(f"⏭️ Skipping: missing proj/id/patch.")
        return

    logger.info(f"=== 🔍 Non-patch fix for {pid}-{bid} ===")
    # checkout
    origin = checkout_version(pid, bid)
    test_repo = os.path.join(TEMP_DIR, f"{pid.lower()}_{bid}_test")
    if os.path.exists(test_repo):
        shutil.rmtree(test_repo)
    shutil.copytree(origin, test_repo)

    # locate scopes for oracle
    diff_file = f"./framework/projects/{pid}/patches/{bid}.src.patch"
    scopes = locate_by_patch(diff_file, test_repo)
    # flatten scopes in order
    entries = []  # list of (filename, start, end)
    for filename, scope_list in sorted(scopes.items()):
        for name, type, start, end in scope_list:
            entries.append((filename, start, end))

    # extract replacements
    hunks = extract_hunks(patch_text)
    # apply each hunk
    for filename, idx, repl in hunks:
        if idx < 0 or idx >= len(entries):
            logger.warning(f"Invalid hunk idx {idx} for {filename}")
            output_data.append({
                "proj": pid,
                "id": bid,
                "hunks": hunks,
                "scopes": scopes,
                "result": "invalid_hunk",
                "information": f"Invalid hunk index {idx} for {filename}"
            })
            return
        file_path = os.path.join(test_repo, entries[idx][0])
        start, end = entries[idx][1], entries[idx][2]
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            # replacement lines
            new_lines = [l + '\n' for l in repl.splitlines()]
            # adjust by index (1-based)
            lines[start-1:end] = new_lines
            with open(file_path, 'w') as f:
                f.writelines(lines)
            logger.info(f"Applied hunk {idx} to {filename}")
        except Exception as e:
            logger.error(f"Error applying hunk {idx} to {filename}: {e}")

    # run tests
    try:
        result = subprocess.run(
            ["defects4j", "test"],
            cwd=test_repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out = result.stdout
        if "Failing tests: 0" in out:
            logger.info(f"🎉 {pid}-{bid} PASSED all tests.")
            output_data.append({
                "proj": pid,
                "id": bid,
                "hunks": hunks,
                "scopes": scopes,
                "result": "passed",
                "information": out
            })
        else:
            logger.info(f"❌ {pid}-{bid} did NOT fix the bug.")
            output_data.append({
                "proj": pid,
                "id": bid,
                "hunks": hunks,
                "scopes": scopes,
                "result": "failed",
                "information": out
            })
    except Exception as e:
        logger.error(f"Error running tests for {pid}-{bid}: {e}")
        output_data.append({
            "proj": pid,
            "id": bid,
            "hunks": hunks,
            "scopes": scopes,
            "result": "error",
            "information": str(e)
        })


def main(data_json, pred_jsonl, output_dir="./output_notpatch"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(output_dir, "eval_notpatch.log")),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    with open(data_json) as f:
        data_list = json.load(f)

    with open(pred_jsonl) as f:
        pred_list = [json.loads(line) for line in f]

    if len(data_list) != len(pred_list):
        logger.error("Data and prediction count mismatch.")
        return

    output_json = os.path.join(output_dir, "eval_notpatch_results.json")

    for i, (data, pred) in enumerate(zip(data_list, pred_list)):
        try:
            future = executor.submit(apply_replacements, data, pred, logger)
            future.result(timeout=TIMEOUT)
        except TimeoutError:
            logger.error(f"⏰ Timeout for {data.get('proj')}-{data.get('id')}")
            output_data.append({
                "proj": data.get('proj'),
                "id": data.get('id'),
                "result": "timeout"
            })
        except Exception as e:
            logger.error(f"🚨 Error: {e}")
        finally:
            with open(output_json, 'w') as f:
                json.dump(output_data, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_json", required=True)
    parser.add_argument("--pred_jsonl", required=True)
    args = parser.parse_args()
    main(args.data_json, args.pred_jsonl)
