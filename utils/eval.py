import os
import json
import subprocess
import argparse
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from checkout_version import TEMP_DIR, checkout_version


TIMEOUT = 60 * 5  # 5 minutes


def extract_patch(patch_text):
    # Extract the patch from <patch>...</patch> tags
    start = patch_text.find("<patch>")
    end = patch_text.find("</patch>")
    if start == -1 or end == -1:
        print("⚠️ No <patch> tag found in the patch text.")
        return patch_text
    return patch_text[start + len("<patch>"):end].strip()


def apply_patch(repo_dir, patch_text):
    patch_file = os.path.join(repo_dir, "temp.patch")
    with open(patch_file, "w") as f:
        f.write(patch_text)
    try:
        subprocess.run(
            ["patch", "-p1", "-F", "5", "-l", "-r", "-", "-i", "temp.patch"],
            cwd=repo_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except subprocess.CalledProcessError as e:
        print("⚠️ Patch apply failed:", e.stderr.decode())
        return False
    finally:
        os.remove(patch_file)


def run_defects4j_tests(repo_dir):
    try:
        result = subprocess.run(
            ["defects4j", "test"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return result.stdout, result.returncode
    except Exception as e:
        return str(e), -1


output_data = []


def test_bug_fix(i, data, pred, logger):
    global output_data
    pid = data.get("proj")
    bid = str(data.get("id"))
    patch = extract_patch(pred.get("predict"))

    if not (pid and bid and patch):
        logger.info(f"⏭️ Skipping #{i}: missing proj/id/patch.")
        return

    logger.info(f"=== 🔍 Patch #{i} for {pid}-{bid} ===")

    logger.info(f"📦 Checking out {pid}-{bid}...")
    origin_repo = checkout_version(pid, bid)
    test_repo = os.path.join(TEMP_DIR, f"{pid.lower()}_{bid}_test")
    if os.path.exists(test_repo):
        shutil.rmtree(test_repo)
    shutil.copytree(origin_repo, test_repo)

    if apply_patch(test_repo, patch):
        logger.info("✅ Patch applied. Running tests...")
        output, _ = run_defects4j_tests(test_repo)
        logger.info(output)
        if "Failing tests: 0" in output:
            logger.info(f"🎉 Patch #{i} for {pid}-{bid} PASSED all tests.")
            output_data.append({
                "proj": pid,
                "id": bid,
                "patch": patch,
                "result": "passed",
                "information": output
            })
        else:
            logger.info(f"❌ Patch #{i} for {pid}-{bid} did NOT fix the bug.")
            output_data.append({
                "proj": pid,
                "id": bid,
                "patch": patch,
                "result": "failed",
                "information": output
            })
    else:
        logger.warning(f"❌ Failed to apply patch #{i} for {pid}-{bid}.")
        output_data.append({
            "proj": pid,
            "id": bid,
            "patch": patch,
            "result": "failed",
            "information": "Patch application failed."
        })


executor = ThreadPoolExecutor(max_workers=1)


def main(data_json, pred_jsonl, output_dir="./output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(output_dir, "eval.log")),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting evaluation...")
    logger.info(f"Data JSON: {data_json}")
    logger.info(f"Predictions JSONL: {pred_jsonl}")

    with open(data_json, "r") as f_data:
        data_list = json.load(f_data)

    with open(pred_jsonl, "r") as f_pred:
        pred_list = [json.loads(line) for line in f_pred]

    if len(data_list) != len(pred_list):
        logger.error(f"❌ Mismatch: {len(data_list)} data entries vs {len(pred_list)} predictions.")
        return

    output_json = os.path.join(output_dir, "eval_results.json")

    for i, (data, pred) in enumerate(zip(data_list, pred_list)):
        try:
            future = executor.submit(test_bug_fix, i, data, pred, logger)
            future.result(timeout=TIMEOUT)
        except TimeoutError:
            logger.error(f"⏰ Timeout at #{i}: {data['proj']}-{data['id']}")
            output_data.append({
                "proj": data["proj"],
                "id": data["id"],
                "patch": pred.get("predict"),
                "result": "timeout",
                "information": "Test timed out."
            })
        except Exception as e:
            logger.error(f"🚨 Error at #{i}: {e}")
        finally:
            # write the output to JSON file
            with open(output_json, "w") as f_out:
                json.dump(output_data, f_out, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_json", help="Original ShareGPT-style JSON file with proj/id")
    parser.add_argument("--pred_jsonl", help="Model predictions JSONL file with patch")
    args = parser.parse_args()
    main(args.data_json, args.pred_jsonl)
