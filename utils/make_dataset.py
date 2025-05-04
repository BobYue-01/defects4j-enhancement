import logging
from tqdm import tqdm
from process_instance import process_instance
from json_file import load_file, save_to_file


def make_dataset(
    method="oracle",
    instance_file="issues.json",
    output_dir="dataset.json",
):
    """
    处理 instances 中的每一行，生成数据集
    """
    logger = logging.getLogger(__name__)
    data = []

    # 读取现有 issues 数据
    instances = load_file(instance_file)

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
        instance_file="issues.json",
        output_dir="dataset.json",
    )
    logging.info("数据集处理完成，保存到 dataset.json")
