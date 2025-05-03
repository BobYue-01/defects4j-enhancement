import os
import json
import subprocess
import pandas as pd
import logging
from tqdm import tqdm
from fetch_issue import fetch_issue


IDENTIFIERS = [
    "Chart",
    "Cli",
    "Closure",
    "Codec",
    "Collections",
    "Compress",
    "Csv",
    "Gson",
    "JacksonCore",
    "JacksonDatabind",
    "JacksonXml",
    "Jsoup",
    "JxPath",
    "Lang",
    "Math",
    "Mockito",
    "Time",
]


def load_file(file):
    """
    读取 JSON 文件，返回 DataFrame
    """
    df = pd.DataFrame(columns=[
        "proj", "id", "classes_modified", "url", "title", "description"
    ])
    if not os.path.exists(file):
        return df
    else:
        with open(file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                df = pd.DataFrame(data)
                print(f"文件 {file} 已存在，读取 {len(df)} 行数据")
                return df
            except json.JSONDecodeError:
                print(f"文件 {file} 格式不正确")
                return df


def save_to_file(file, df):
    """
    将 DataFrame 保存为 JSON 文件
    """
    with open(file, 'w', encoding='utf-8') as f:
        df.drop_duplicates(subset=["proj", "id"], keep="last", inplace=True)
        df["id"] = df["id"].astype(int)
        df.sort_values(by=["proj", "id"], inplace=True)
        df.replace("\r\n", "\n", regex=True, inplace=True)
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=4)


def fetch_all_issues(file, df):
    """
    获取所有项目的 issue URL 和标题描述
    """
    logger = logging.getLogger(__name__)
    issues = []

    try:
        for identifier in IDENTIFIERS:
            bugs = subprocess.run(
                f'./framework/bin/defects4j query -p {identifier} -q "report.url,classes.modified"',
                shell=True,
                capture_output=True
            ).stdout.decode().splitlines()
            logger.info(f"项目 {identifier} 有 {len(bugs)} 个 bug")
            for bug in tqdm(bugs):
                id, url, classes_modified = bug.split(',')
                id = int(id.strip())
                classes_modified = classes_modified.strip('"')
                condition = (df["proj"] == identifier) & (df["id"] == id)
                s = df[condition]
                if s.shape[0] > 0 and s["title"].values[0] != "" and s["description"].values[0] != "":
                    df.loc[condition, "classes_modified"] = classes_modified
                    logger.info(f"跳过已存在的 {id} 的 {url}")
                    logger.info(f"更新 {id} 的 classes_modified 为 {classes_modified}")
                    continue
                try:
                    title, description = fetch_issue(url)
                    issues.append({
                        "proj": identifier,
                        "id": id,
                        "classes_modified": classes_modified,
                        "url": url,
                        "title": title,
                        "description": description
                    })
                except Exception as e:
                    logger.error(f"获取 {id} 的 {url} 失败: {e}")
                    continue
    except KeyboardInterrupt:
        logger.warning("用户中止操作")
    finally:
        if issues:
            logger.info(f"共获取到 {len(issues)} 个新 issue")
            new_issues_df = pd.DataFrame(issues)
            df = pd.concat([df, new_issues_df], ignore_index=True)
        save_to_file(file, df)
        logger.info(f"已写入文件 {file}")


if __name__ == "__main__":
    logging.basicConfig(filename='fetch_issues.log', level=logging.INFO)
    file = "issues.json"
    df = load_file(file)
    fetch_all_issues(file, df)
