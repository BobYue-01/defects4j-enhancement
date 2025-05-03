def locate_oracle(classes_modified):
    """
    Oracle extraction function.
    """
    # e.g. "org.apache.commons.csv.CSVFormat;org.apache.commons.csv.CSVPrinter"
    classes = classes_modified.split(';')
    oracle_files = [
        f"{cls.replace('.', '/')}.java" for cls in classes
    ]
    return oracle_files


if __name__ == "__main__":
    # Example usage
    classes_modified = "org.apache.commons.csv.CSVFormat;org.apache.commons.csv.CSVPrinter"
    oracle_files = locate_oracle(classes_modified)
    print(f"Oracle files: {oracle_files}")
