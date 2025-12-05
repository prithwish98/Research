import os
import re
import argparse

# Core function to move commas from end to start of each column definition
def move_commas_to_start(ddl: str) -> str:
    lines = ddl.split('
')
    transformed_lines = []

    for line in lines:
        if re.search(r',\s*$', line):
            line = re.sub(r',\s*$', '', line)
            stripped = line.lstrip()
            indent = line[:len(line) - len(stripped)]
            line = f"{indent},{stripped}"
        transformed_lines.append(line)

    return '
'.join(transformed_lines)

# Process a single file
def process_file(input_file: str, output_file: str):
    with open(input_file, 'r', encoding='utf-8') as f:
        ddl_content = f.read()
    transformed = move_commas_to_start(ddl_content)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(transformed)
    print(f"Processed file: {input_file} -> {output_file}")

# Process all .sql files in a folder
def process_folder(input_folder: str, output_folder: str):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.sql'):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename.replace('.sql', '_formatted.sql'))
            process_file(input_path, output_path)

# CLI implementation
def main():
    parser = argparse.ArgumentParser(description="Move commas from end to start in DDL column definitions.")
    parser.add_argument('--input', required=True, help="Input string, file path, or folder path")
    parser.add_argument('--output', required=False, help="Output file or folder path")
    parser.add_argument('--mode', choices=['string', 'file', 'folder'], required=True, help="Mode of operation")

    args = parser.parse_args()

    if args.mode == 'string':
        transformed = move_commas_to_start(args.input)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(transformed)
            print(f"Transformed DDL saved to {args.output}")
        else:
            print(transformed)

    elif args.mode == 'file':
        if not args.output:
            raise ValueError("Output file path is required for file mode.")
        process_file(args.input, args.output)

    elif args.mode == 'folder':
        if not args.output:
            raise ValueError("Output folder path is required for folder mode.")
        process_folder(args.input, args.output)

if __name__ == "__main__":
    main()
