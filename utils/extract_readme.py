import os
from extract_pom import extract_pom


def extract_readme(path):
    """
    Extract the README file in the given path.
    """
    readme_files = [
        "README.md",
        "README.txt",
        "README",
    ]

    for readme_file in readme_files:
        full_path = os.path.join(path, readme_file)
        if os.path.exists(full_path):
            return readme_file, open(full_path, "r").read()

    pom_path = os.path.join(path, "pom.xml")
    if os.path.exists(pom_path):
        return "pom.xml", extract_pom(pom_path)

    return None
