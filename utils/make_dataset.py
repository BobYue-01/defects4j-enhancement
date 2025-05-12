import logging
from tqdm import tqdm
from process_instance import process_instance
from json_file import load_file, save_to_file


def make_dataset(
    method="file",
    swe_like=True,
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
        text = process_instance(instance, method, swe_like)
        if text:
            data.append({
                "proj": instance["proj"],
                "id": instance["id"],
                "text": text,
            })

    save_to_file(output_dir, data)


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(
        filename='make_dataset.log', 
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 处理数据集
    make_dataset(
        method="file",
        swe_like=True,
        instance_file="issues.json",
        output_dir="oracle_file_swe_dataset.json",
    )
    make_dataset(
        method="file",
        swe_like=False,
        instance_file="issues.json",
        output_dir="oracle_file_dataset.json",
    )
    # make_dataset(
    #     method="scope",
    #     swe_like=True,
    #     instance_file="issues.json",
    #     output_dir="oracle_scope_swe_dataset.json",
    # )
    # make_dataset(
    #     method="scope",
    #     swe_like=False,
    #     instance_file="issues.json",
    #     output_dir="oracle_scope_dataset.json",
    # )
    logging.info("数据集处理完成")
