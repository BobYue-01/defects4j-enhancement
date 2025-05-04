import logging
from tqdm import tqdm
from process_instance import process_instance
from json_file import load_file, save_to_file


def make_sharegpt_dataset(
    orginal_file="dataset.json",
    output_dir="sharegpt_dataset.json",
):
    """
    处理 instances 中的每一行，生成 sharegpt 格式数据集
    """
    logger = logging.getLogger(__name__)
    data = []

    # 读取现有数据集
    instances = load_file(orginal_file)

    # 处理每一行
    for _, instance in tqdm(enumerate(instances), total=len(instances)):
        text = instance["text"]
        if text:
            data.append({
                "proj": instance["proj"],
                "id": instance["id"],
                "conversations": [
                    {
                        "from": "human",
                        "value": text,
                    },
                    {
                        "from": "gpt",
                        "value": "",
                    }
                ],
            })

    save_to_file(output_dir, data)
    logger.info(f"数据集已保存到 {output_dir}")


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(filename='make_sharegpt_dataset.log', level=logging.INFO)

    # 处理数据集
    make_sharegpt_dataset(
        orginal_file="dataset.json",
        output_dir="sharegpt_dataset.json",
    )
    logging.info("数据集处理完成，保存到 sharegpt_dataset.json")
