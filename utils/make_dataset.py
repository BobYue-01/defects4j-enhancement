import json
import logging
from tqdm import tqdm
from process_instance import process_instance


def load_file(file):
    """
    读取 JSON 文件
    """
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data


def save_to_file(file, json_data):
    """
    保存为 JSON 文件
    """
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
        print(f"数据已保存到 {file}")


def make_dataset(
    method="oracle",
    output_dir="dataset",
    file_name="issues.json",
):
    """
    处理 instances 中的每一行，生成数据集
    """
    logger = logging.getLogger(__name__)
    data = []

    # 读取现有数据集
    instances = load_file(file_name)

    # 处理每一行
    for _, instance in tqdm(enumerate(instances), total=len(instances)):
        logger.info(f"处理项目 {instance['proj']}，缺陷 ID {instance['id']}")
        text = process_instance(instance, method)
        if text:
            data.append({
                "proj": instance["proj"],
                "id": instance["id"],
                "text": text,
            })

    save_to_file(output_dir, data)


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(filename='make_dataset.log', level=logging.INFO)

    # 处理数据集
    make_dataset(
        method="oracle",
        output_dir="dataset.json",
        file_name="issues.json",
    )
    logging.info("数据集处理完成，保存到 dataset.json")
