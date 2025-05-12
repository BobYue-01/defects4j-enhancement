import os
import json
import subprocess
import tempfile
import argparse
import shutil

def apply_patch(repo_dir, patch_text):
    patch_file = os.path.join(repo_dir, "temp.patch")
    with open(patch_file, "w") as f:
        f.write(patch_text)
    try:
        subprocess.run(
            ["patch", "-p1", "-i", patch_file],
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

def checkout_project(proj, bug_id, base_dir):
    work_dir = os.path.join(base_dir, f"{proj}_{bug_id}")
    if not os.path.exists(work_dir):
        print(f"📦 Checking out {proj}-{bug_id}...")
        subprocess.run([
            "defects4j", "checkout",
            "-p", proj,
            "-v", f"{bug_id}b",
            "-w", work_dir
        ], check=True)
    return work_dir

def main(data_json, pred_jsonl):
    base_checkout_dir = tempfile.mkdtemp(prefix="defects4j_batch_")

    with open(data_json, "r") as f_data:
        data_list = json.load(f_data)

    with open(pred_jsonl, "r") as f_pred:
        pred_list = [json.loads(line) for line in f_pred]

    if len(data_list) != len(pred_list):
        print(f"❌ Mismatch: {len(data_list)} data entries vs {len(pred_list)} predictions.")
        return

    for i, (data, pred) in enumerate(zip(data_list, pred_list)):
        try:
            proj = data.get("proj")
            bug_id = str(data.get("id"))
            patch = pred.get("predict")

            if not (proj and bug_id and patch):
                print(f"⏭️ Skipping #{i}: missing proj/id/patch.")
                continue

            print(f"\n=== 🔍 Patch #{i} for {proj}-{bug_id} ===")

            origin_repo = checkout_project(proj, bug_id, base_checkout_dir)
            test_repo = os.path.join(base_checkout_dir, f"{proj}_{bug_id}_test_{i}")
            shutil.copytree(origin_repo, test_repo)

            if apply_patch(test_repo, patch):
                print("✅ Patch applied. Running tests...")
                output, _ = run_defects4j_tests(test_repo)
                print(output)
                if "Failing tests: 0" in output:
                    print(f"🎉 Patch #{i} for {proj}-{bug_id} PASSED all tests.")
                else:
                    print(f"❌ Patch #{i} for {proj}-{bug_id} did NOT fix the bug.")
            else:
                print(f"❌ Failed to apply patch #{i} for {proj}-{bug_id}.")

        except Exception as e:
            print(f"🚨 Error at #{i}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_json", help="Original ShareGPT-style JSON file with proj/id")
    parser.add_argument("--pred_jsonl", help="Model predictions JSONL file with patch")
    args = parser.parse_args()
    main(args.data_json, args.pred_jsonl)
