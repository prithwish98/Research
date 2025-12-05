
import os
import re
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# Core function
def move_commas_to_start(ddl: str) -> str:
    lines = ddl.split('\n')
    transformed_lines = []
    inside_columns = False
    first_column = True

    for line in lines:
        stripped_line = line.strip()

        if stripped_line.endswith('('):
            inside_columns = True
            transformed_lines.append(line)
            continue

        if stripped_line.startswith(')'):
            inside_columns = False
            transformed_lines.append(line)
            continue

        if inside_columns:
            line = re.sub(r',\s*$', '', line)

            if first_column:
                transformed_lines.append(line)
                first_column = False
            else:
                stripped = line.lstrip()
                indent = line[:len(line) - len(stripped)]
                line = f"{indent},{stripped}"
                transformed_lines.append(line)
        else:
            transformed_lines.append(line)

    return '\n'.join(transformed_lines)

def process_file(input_file: str) -> str:
    with open(input_file, 'r', encoding='utf-8') as f:
        ddl_content = f.read()
    return move_commas_to_start(ddl_content)

def process_folder(input_folder: str, output_folder: str):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.sql'):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename.replace('.sql', '_formatted.sql'))
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(process_file(input_path))

# GUI
def launch_gui():
    def convert_string():
        ddl = text_input.get("1.0", tk.END).strip()
        if not ddl:
            messagebox.showerror("Error", "Please enter DDL text.")
            return
        transformed = move_commas_to_start(ddl)
        text_output.delete("1.0", tk.END)
        text_output.insert(tk.END, transformed)

    def save_output():
        output_file = filedialog.asksaveasfilename(defaultextension=".sql", filetypes=[("SQL Files", "*.sql")])
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text_output.get("1.0", tk.END))
            messagebox.showinfo("Success", f"Output saved to {output_file}")

    def copy_output():
        root.clipboard_clear()
        root.clipboard_append(text_output.get("1.0", tk.END))
        root.update()
        messagebox.showinfo("Copied", "Output copied to clipboard")

    def handle_drop(event):
        path = event.data.strip('{}')
        if os.path.isfile(path):
            transformed = process_file(path)
            text_output.delete("1.0", tk.END)
            text_output.insert(tk.END, transformed)
        elif os.path.isdir(path):
            output_folder = filedialog.askdirectory(title="Select Output Folder")
            if output_folder:
                process_folder(path, output_folder)
                messagebox.showinfo("Success", f"All .sql files processed and saved to {output_folder}")

    root = tk.Tk()
    root.title("DDL Formatter - Move Commas to Start")

    frame = tk.Frame(root)
    frame.pack(pady=10)

    tk.Label(frame, text="Paste DDL Here:").pack()
    text_input = scrolledtext.ScrolledText(frame, width=100, height=15)
    text_input.pack()

    tk.Button(frame, text="Convert String", command=convert_string).pack(pady=5)

    tk.Label(frame, text="Converted DDL:").pack()
    text_output = scrolledtext.ScrolledText(frame, width=100, height=15)
    text_output.pack()

    tk.Button(frame, text="Save Output", command=save_output).pack(pady=5)
    tk.Button(frame, text="Copy Output", command=copy_output).pack(pady=5)

    tk.Label(frame, text="Drag and Drop a File or Folder Below:").pack(pady=10)
    drop_area = tk.Label(frame, text="Drop Here", relief="solid", width=50, height=5)
    drop_area.pack(pady=10)

    # Enable drag and drop using tkinterdnd2 if available
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk()
        drop_area.drop_target_register(DND_FILES)
        drop_area.dnd_bind('<<Drop>>', handle_drop)
    except ImportError:
        drop_area.config(text="Drag-and-drop requires tkinterdnd2 module")

    root.mainloop()

# CLI
def main():
    parser = argparse.ArgumentParser(description="Move commas from end to start in DDL column definitions.")
    parser.add_argument('--input', help="Input string, file path, or folder path")
    parser.add_argument('--output', help="Output file or folder path")
    parser.add_argument('--mode', choices=['string', 'file', 'folder'], help="Mode of operation")
    parser.add_argument('--gui', action='store_true', help="Launch GUI mode")

    args = parser.parse_args()

    if args.gui:
        launch_gui()
    else:
        if not args.mode or not args.input:
            print("Error: --mode and --input are required unless --gui is used.")
            return

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
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(process_file(args.input))

        elif args.mode == 'folder':
            if not args.output:
                raise ValueError("Output folder path is required for folder mode.")
            process_folder(args.input, args.output)

if __name__ == "__main__":
    main()
