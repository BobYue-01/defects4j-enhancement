import xml.etree.ElementTree as ET


def extract_pom(path):
    """
    Extracts the POM description from a given path.
    """
    with open(path, 'r') as file:
        try:
            content = file.read()
            root = ET.fromstring(content)
            ns = {'mvn': root.tag.split('}')[0].strip('{')}
            description = root.find('mvn:description', ns)
            if description is not None:
                return description.text.strip()
            else:
                return None
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            return None
        except FileNotFoundError:
            print(f"File not found: {path}")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None


if __name__ == "__main__":
    # Example usage
    pom_path = '/tmp/lang_1_buggy/pom.xml'
    description = extract_pom(pom_path)
    if description:
        print(f"POM Description: {description}")
    else:
        print("No description found or an error occurred.")
