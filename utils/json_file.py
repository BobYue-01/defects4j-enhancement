import json


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
