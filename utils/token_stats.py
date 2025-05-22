import os
from tqdm import tqdm
from transformers import AutoTokenizer
from json_file import load_file, save_to_file


def get_tokenizer(model_name):
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
    except Exception as e:
        print(f"Error loading tokenizer for model {model_name}: {e}")
        return None
    return tokenizer


def calculate_token_length(tokenizer, text):
    if tokenizer is None:
        print("Tokenizer is not available.")
        return 0
    try:
        tokens = tokenizer.encode(text, add_special_tokens=False)
        token_length = len(tokens)
    except Exception as e:
        print(f"Error calculating token length: {e}")
        return 0
    return token_length


def calculate_token_stats(ds_dir):
    # Load the dataset
    ds = load_file(ds_dir)
    # Initialize the tokenizer
    tokenizer = get_tokenizer("Qwen/Qwen2.5-Coder-0.5B")

    token_lengths = []

    for example in tqdm(ds, desc=f"Processing Dataset {ds_dir}"):
        # Get the text from the dataset
        text = example["text"]
        # Calculate the token length
        token_length = calculate_token_length(tokenizer, text)
        # Append the token length to the list
        token_lengths.append(token_length)

    return token_lengths


def compare_token_lengths(ds_dir_1, ds_dir_2):
    # Load the datasets
    ds_1 = load_file(ds_dir_1)
    ds_2 = load_file(ds_dir_2)
    # Initialize the tokenizer
    tokenizer = get_tokenizer("Qwen/Qwen2.5-Coder-0.5B")

    token_lengths_1 = calculate_token_stats(ds_dir_1)
    token_lengths_2 = calculate_token_stats(ds_dir_2)

    MIN_BIN = 2048

    import matplotlib
    matplotlib.use('TKAgg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    max_length = max(max(token_lengths_1), max(token_lengths_2))
    ks = int(max_length / MIN_BIN) + 4
    bins = range(0, ks * MIN_BIN, MIN_BIN)
    ax.hist(token_lengths_1, bins=bins, color='red', alpha=0.5, log=True, label='Oracle Scope')
    ax.hist(token_lengths_2, bins=bins, color='blue', alpha=0.5, log=True, label='Oracle Scope SWE')
    ax.set_title('Token Length Distribution Comparison')
    ax.set_xlabel('Token Length')
    ax.set_ylabel('Frequency')
    # add line at 32k and 128k
    ax.axvline(x=32768, color='yellow', linestyle='--', label='32k')
    ax.axvline(x=131072, color='red', linestyle='--', label='128k')
    ax.legend()
    fig.savefig('token_length_distribution_comparison.png')
    plt.show()


def stats():
    ds_folder = "datasets"
    # Load the dataset
    ds_token_lengths = load_file(os.path.join(ds_folder, "token_lengths.json"))
    for ds_dir, token_lengths in ds_token_lengths.items():
        print(f"Avg token length for {ds_dir}: {sum(token_lengths) / len(token_lengths)}")
        print(f"Max token length for {ds_dir}: {max(token_lengths)}")


def main():
    ds_folder = "datasets"
    # all ds in the folder
    ds_dirs = os.listdir(ds_folder)
    ds_dirs = [os.path.join(ds_folder, ds_dir) for ds_dir in ds_dirs]
    # calculate token length for each dataset
    ds_token_lengths = {}
    for ds_dir in ds_dirs:
        print(f"Calculating token length for {ds_dir}...")
        token_lengths = calculate_token_stats(ds_dir)
        avg_token_length = sum(token_lengths) / len(token_lengths)
        max_token_length = max(token_lengths)
        print(f"Avg token length for {ds_dir}: {avg_token_length}")
        print(f"Max token length for {ds_dir}: {max_token_length}")
        ds_token_lengths[ds_dir] = {
            "avg_token_length": avg_token_length,
            "max_token_length": max_token_length,
            "all_token_lengths": token_lengths
        }

    save_to_file(os.path.join(ds_folder, "token_lengths.json"), ds_token_lengths)


if __name__ == "__main__":
    main()
