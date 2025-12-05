
import os
import re
import argparse
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

class DDLFormatter:
    """
    A stateless class to format DDL statements.
    - Standardizes CREATE statements to CREATE OR REPLACE.
    - Prefixes table/view names with {{EDW_DB_NAME}}.
    - Moves trailing commas to the start of the next line.
    - Moves opening parenthesis of a CREATE TABLE to a new line.
    """
    def __init__(self):
        self.sql_keywords = {
            'add', 'alter', 'and', 'as', 'asc', 'between', 'by', 'case',
            'char', 'character', 'check', 'column', 'constraint', 'create',
            'date', 'decimal', 'default', 'delete', 'desc', 'distinct',
            'double', 'drop', 'else', 'end', 'exists', 'false', 'float',
            'foreign', 'from', 'group', 'having', 'if', 'in', 'inner',
            'insert', 'int', 'integer', 'into', 'is', 'join', 'key', 'left',
            'like', 'limit', 'not', 'null', 'numeric', 'on', 'or', 'order',
            'outer', 'precision', 'primary', 'references', 'replace', 'right',
            'select', 'set', 'table', 'then', 'timestamp', 'to', 'true',
            'union', 'unique', 'update', 'using', 'values', 'varchar',
            'view', 'when', 'where', 'with'
        }
        # Regex to find whole-word keywords, case-insensitively
        self.keyword_regex = re.compile(r'\b(' + '|'.join(self.sql_keywords) + r')\b', re.IGNORECASE)
        self.create_statement_regex = re.compile(
            r'(CREATE(?:.|\s)+?(?:TABLE|VIEW)(?:\s+IF\s+NOT\s+EXISTS)?\s+)([^\s(]+)(.*)', re.IGNORECASE
        )

    def _uppercase_keywords(self, line: str) -> str:
        """
        Converts all recognized SQL keywords in a line to uppercase.
        """
        return self.keyword_regex.sub(lambda match: match.group(0).upper(), line)

    def _process_create_statement(self, line: str) -> str:
        """
        Processes a CREATE TABLE or CREATE VIEW line to standardize it.
        """
        match = self.create_statement_regex.search(line)
        if not match:
            return line

        prefix, identifier, suffix = match.groups()

        # Determine if it's a TABLE or VIEW for the replacement string
        is_view = 'view' in prefix.lower()
        statement_type = 'VIEW' if is_view else 'TABLE'

        # Standardize to CREATE OR REPLACE
        if ' or replace ' not in prefix.lower():
            prefix = f'CREATE OR REPLACE {statement_type} '

        # Prepend database name
        parts = identifier.split('.')
        if len(parts) in [1, 2]:  # schema.table or just table
            new_identifier = f"{{{{EDW_DB_NAME}}}}.{identifier}"
        elif len(parts) == 3:  # db.schema.table
            new_identifier = f"{{{{EDW_DB_NAME}}}}.{'.'.join(parts[1:])}"
        else:
            return line

        return prefix + new_identifier + suffix

    def format(self, ddl: str) -> str:
        lines = ddl.split('\n')
        transformed_lines = []
        inside_columns = False
        first_column = True

        for line in lines:
            stripped_line = line.strip()

            # Uppercase keywords first, except for the Jinja variable
            line = self._uppercase_keywords(line).replace('{{EDW_DB_NAME}}', '{{edw_db_name}}')

            if self.create_statement_regex.search(line):
                line = self._process_create_statement(line)
                stripped_line = line.strip()

            if not inside_columns and stripped_line.rstrip().endswith('('):
                # If the CREATE TABLE line ends with '(', move '(' to a new line.
                inside_columns = True
                first_column = True

                # Find the position of '(' and split the line
                paren_pos = line.rfind('(')
                create_line_part = line[:paren_pos].rstrip()
                indent = line[:len(line) - len(line.lstrip())]

                if create_line_part:
                    transformed_lines.append(create_line_part)
                transformed_lines.append(f"{indent}(")
                continue

            if inside_columns and stripped_line.startswith(')'):
                inside_columns = False
                transformed_lines.append(line)
                continue

            if inside_columns and stripped_line:
                line = re.sub(r',\s*$', '', line)

                if first_column:
                    transformed_lines.append(line)
                    first_column = False
                else:
                    stripped = line.lstrip()
                    indent = line[:len(line) - len(stripped)]
                    transformed_lines.append(f"{indent},{stripped}")
            else:
                transformed_lines.append(line)

        return '\n'.join(transformed_lines)

class DDLFormatterApp:
    def __init__(self, root):
        self.root = root
        self.formatter = DDLFormatter()
        self._setup_ui()

    def _setup_ui(self):
        self.root.title("DDL Formatter")
        self.root.geometry("1400x800")
        self.root.configure(bg="#f0f0f0")

        heading_font = ("Segoe UI", 16, "bold")
        font_style = ("Segoe UI", 14)

        self._create_menu()

        # --- Layout Frames ---
        # Status bar at the very bottom
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W, font=("Segoe UI", 10))
        self.status_bar.pack(side="bottom", fill="x")

        # Progress bar (initially hidden)
        self.progress_bar = ttk.Progressbar(self.root, orient='horizontal', mode='determinate')
        # self.progress_bar.pack(side="bottom", fill="x", padx=10, pady=5) # Packed later when needed

        # Frame for main action buttons
        button_frame = tk.Frame(self.root, bg="#f0f0f0")
        button_frame.pack(side="bottom", fill="x", pady=(5, 10))

        # Split screen for input and output
        main_frame = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg="#f0f0f0")
        main_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # --- Widgets ---
        # Input pane
        input_frame = tk.LabelFrame(main_frame, text="Input DDL", font=heading_font, padx=10, pady=10, bg="#f0f0f0")
        main_frame.add(input_frame, width=700)
        self.text_input = scrolledtext.ScrolledText(input_frame, width=90, height=40, font=font_style)
        self.text_input.pack(fill="both", expand=True)

        # Output pane
        output_frame = tk.LabelFrame(main_frame, text="Formatted DDL", font=heading_font, padx=10, pady=10, bg="#f0f0f0")
        main_frame.add(output_frame)
        self.text_output = scrolledtext.ScrolledText(output_frame, width=90, height=40, font=font_style)
        self.text_output.pack(fill="both", expand=True)

        # Action buttons configuration
        convert_button = tk.Button(button_frame, text="Format", command=self.convert_string, font=("Segoe UI", 12, "bold"), bg="#4CAF50", fg="white", padx=10, pady=5)
        clear_button = tk.Button(button_frame, text="Clear", command=self.clear_text_areas, font=("Segoe UI", 12), padx=10, pady=5)
        button_frame.grid_columnconfigure(0, weight=1)
        convert_button.grid(row=0, column=1, padx=5)
        clear_button.grid(row=0, column=2, padx=5)
        button_frame.grid_columnconfigure(3, weight=1)

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Browse File...", command=self.browse_file)
        file_menu.add_command(label="Browse Folder...", command=self.browse_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        actions_menu = tk.Menu(menubar, tearoff=0)
        actions_menu.add_command(label="Save Output As...", command=self.save_output)
        actions_menu.add_command(label="Copy Output", command=self.copy_output)
        menubar.add_cascade(label="Actions", menu=actions_menu)

    def update_status(self, message, duration=4000):
        self.status_bar.config(text=message)
        if duration:
            self.status_bar.after(duration, lambda: self.status_bar.config(text="Ready"))

    def convert_string(self):
        ddl = self.text_input.get("1.0", tk.END).strip()
        if not ddl:
            messagebox.showerror("Error", "Please enter DDL text.")
            return
        transformed = self.formatter.format(ddl)
        self.text_output.delete("1.0", tk.END)
        self.text_output.insert(tk.END, transformed)
        self.update_status("DDL formatted successfully.")

    def clear_text_areas(self):
        self.text_input.delete("1.0", tk.END)
        self.text_output.delete("1.0", tk.END)

    def save_output(self):
        output_file = filedialog.asksaveasfilename(defaultextension=".sql", filetypes=[("SQL Files", "*.sql")])
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(self.text_output.get("1.0", tk.END))
                self.update_status(f"Output saved to {os.path.basename(output_file)}")
            except IOError as e:
                messagebox.showerror("Save Error", f"Could not save file:\n{e}")

    def copy_output(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.text_output.get("1.0", tk.END))
        self.root.update()
        self.update_status("Output copied to clipboard.")

    def browse_file(self):
        input_file = filedialog.askopenfilename(filetypes=[("SQL Files", "*.sql")])
        if input_file:
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert(tk.END, content)
                self.convert_string()
                self.update_status(f"Loaded and formatted file: {os.path.basename(input_file)}")
            except Exception as e:
                messagebox.showerror("File Error", f"Could not read or process file:\n{e}")

    def browse_folder(self):
        input_folder = filedialog.askdirectory(title="Select Input Folder")
        if not input_folder:
            return
        output_folder = filedialog.askdirectory(title="Select Output Folder")
        if not output_folder:
            return
        
        # Run folder processing in a separate thread to avoid freezing the GUI
        thread = threading.Thread(target=self._process_folder_thread, args=(input_folder, output_folder))
        thread.start()

    def _process_folder_thread(self, input_folder, output_folder):
        try:
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            sql_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.sql')]
            if not sql_files:
                messagebox.showinfo("Information", "No .sql files found in the selected input folder.")
                return

            self.progress_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
            self.progress_bar['maximum'] = len(sql_files)

            last_input_content, last_output_content = "", ""
            for i, filename in enumerate(sql_files):
                self.update_status(f"Processing {i+1}/{len(sql_files)}: {filename}", duration=None)
                self.progress_bar['value'] = i + 1
                self.root.update_idletasks()

                input_path = os.path.join(input_folder, filename)
                with open(input_path, 'r', encoding='utf-8') as f:
                    last_input_content = f.read()
                
                last_output_content = self.formatter.format(last_input_content)
                
                output_filename = filename.replace('.sql', '_formatted.sql') if '.sql' in filename.lower() else f"{filename}_formatted.sql"
                output_path = os.path.join(output_folder, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(last_output_content)

            # Update GUI with the last processed file
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert(tk.END, last_input_content)
            self.text_output.delete("1.0", tk.END)
            self.text_output.insert(tk.END, last_output_content)

            messagebox.showinfo("Success", f"Processed {len(sql_files)} .sql file(s) and saved to {output_folder}.\nShowing the last processed file.")

        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred during folder processing:\n{e}")
        finally:
            self.progress_bar.pack_forget()
            self.update_status("Ready")

def process_cli(args, formatter):
    """Handles command-line interface operations."""
    if not args.input:
        print("Error: --input is required for non-GUI mode.")
        return

    if args.mode == 'string':
        formatted_ddl = formatter.format(args.input)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(formatted_ddl)
            print(f"Formatted DDL saved to {args.output}")
        else:
            print(formatted_ddl)

    elif args.mode in ['file', 'folder']:
        if not args.output:
            print(f"Error: --output is required for {args.mode} mode.")
            return

        if args.mode == 'file':
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    content = f.read()
                formatted_ddl = formatter.format(content)
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(formatted_ddl)
                print(f"File '{args.input}' formatted and saved to '{args.output}'.")
            except FileNotFoundError:
                print(f"Error: Input file not found at '{args.input}'")
            except Exception as e:
                print(f"An error occurred: {e}")

        elif args.mode == 'folder':
            if not os.path.isdir(args.input):
                print(f"Error: Input path '{args.input}' is not a valid directory.")
                return
            if not os.path.exists(args.output):
                os.makedirs(args.output)
            
            print(f"Processing files from '{args.input}' and saving to '{args.output}'...")
            for filename in os.listdir(args.input):
                if filename.lower().endswith('.sql'):
                    input_path = os.path.join(args.input, filename)
                    output_path = os.path.join(args.output, filename.replace('.sql', '_formatted.sql'))
                    with open(input_path, 'r', encoding='utf-8') as f_in:
                        content = f_in.read()
                    formatted_ddl = formatter.format(content)
                    with open(output_path, 'w', encoding='utf-8') as f_out:
                        f_out.write(formatted_ddl)
                    print(f"  - Formatted {filename}")
            print("Done.")

def main():
    parser = argparse.ArgumentParser(description="A tool to format SQL DDL files.")
    parser.add_argument('--input', help="Input string, file path, or folder path")
    parser.add_argument('--output', help="Output file or folder path")
    parser.add_argument('--mode', choices=['string', 'file', 'folder'], default='string', help="Mode of operation for CLI")
    parser.add_argument('--gui', action='store_true', help="Launch GUI mode")

    args = parser.parse_args()

    if args.gui:
        root = tk.Tk()
        app = DDLFormatterApp(root)
        root.mainloop()
    else:
        formatter = DDLFormatter()
        process_cli(args, formatter)

if __name__ == "__main__":
    main()
