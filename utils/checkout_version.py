import os
import shutil
import logging
import subprocess


TEMP_DIR = "/tmp/defects4j_checkout"


def checkout_version(pid, bid, version_suffix="b", force=False):
    """
    Checkout the specified project version using defects4j.
    version_suffix can be "b" (buggy) or "f" (fixed).
    """
    logger = logging.getLogger(__name__)

    version = f"{bid}{version_suffix}"
    checkout_dir = os.path.join(
        TEMP_DIR,
        f"{pid.lower()}_{bid}_{"buggy" if version_suffix == "b" else "fixed"}"
    )

    if os.path.exists(checkout_dir):
        if force:
            shutil.rmtree(checkout_dir)
            logger.debug(f"已存在检出目录，强制检出：{pid} {version}")
        else:
            logger.debug(f"已存在检出目录：{checkout_dir}")
            return checkout_dir
    os.makedirs(checkout_dir, exist_ok=True)

    cmd = f"defects4j checkout -p {pid} -v {version} -w {checkout_dir}"

    try:
        subprocess.run(cmd, shell=True, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"检出失败：{pid} {version}，错误：{e}")
        return None
    return checkout_dir


def clear_temp_dir():
    """
    Clear the temporary directory.
    """
    logger = logging.getLogger(__name__)
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        logger.debug(f"临时目录 {TEMP_DIR} 已清除")
    else:
        logger.debug(f"临时目录 {TEMP_DIR} 不存在")


if __name__ == "__main__":
    # Example usage
    pid = "Lang"
    bid = 1
    version_suffix = "b"
    checkout_dir = checkout_version(pid, bid, version_suffix)
    if checkout_dir:
        print(f"检出成功：{checkout_dir}")
    else:
        print("检出失败")
