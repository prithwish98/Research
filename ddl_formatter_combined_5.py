
import os
import re
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# Core function
class DDLFormatter:
    def __init__(self):
        self.inside_columns = False
        self.first_column = True
        # Regex to find CREATE TABLE statements and capture the table name part.
        # It looks for any form of "CREATE...TABLE" and then captures the identifier that follows.
        self.create_table_regex = re.compile(
            r'(CREATE(?:.|\s)+?TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+)([^\s(]+)(.*)', re.IGNORECASE
        )
        self.create_view_regex = re.compile(
            r'(CREATE(?:.|\s)+?VIEW\s+)([^\s(]+)(.*)', re.IGNORECASE
        )

    def _process_create_table_line(self, line: str) -> str:
        match = self.create_table_regex.search(line)
        if not match:
            return line

        prefix = match.group(1)  # The "CREATE ... TABLE " part
        # Standardize to CREATE OR REPLACE TABLE
        if ' or replace ' not in prefix.lower():
            prefix = 'CREATE OR REPLACE TABLE '

        table_identifier = match.group(2) # The table name part
        suffix = match.group(3) # Everything after the table name, like '('
        parts = table_identifier.split('.')

        if len(parts) == 3:  # db.schema.table
            # Replace the first part (database) with the variable
            new_identifier = f"{{{{EDW_DB_NAME}}}}.{'.'.join(parts[1:])}"
        elif len(parts) in [1, 2]:  # schema.table or just table
            # Prepend the variable to the existing schema.table structure
            new_identifier = f"{{{{EDW_DB_NAME}}}}.{table_identifier}"
        else:  # table
            # If only a table is provided, we don't prepend anything as there's no schema.
            # We still need to return the original line to be processed further.
            return line

        return prefix + new_identifier + suffix

    def _process_create_view_line(self, line: str) -> str:
        match = self.create_view_regex.search(line)
        if not match:
            return line

        prefix = match.group(1)  # The "CREATE ... VIEW " part
        # Standardize to CREATE OR REPLACE VIEW
        if ' or replace ' not in prefix.lower():
            prefix = 'CREATE OR REPLACE VIEW '

        view_identifier = match.group(2) # The view name part
        suffix = match.group(3) # Everything after the view name, like 'AS'
        parts = view_identifier.split('.')

        if len(parts) == 3:  # db.schema.view
            new_identifier = f"{{{{EDW_DB_NAME}}}}.{'.'.join(parts[1:])}"
        elif len(parts) in [1, 2]:  # schema.view or just view
            new_identifier = f"{{{{EDW_DB_NAME}}}}.{view_identifier}"
        else:
            return line

        return prefix + new_identifier + suffix

    def move_commas_to_start(self, ddl: str) -> str:
        lines = ddl.split('\n')
        transformed_lines = []

        for line in lines:
            stripped_line = line.strip()
            
            if self.create_table_regex.search(line):
                line = self._process_create_table_line(line)
                stripped_line = line.strip() # Re-strip the line after potential modification
            elif self.create_view_regex.search(line):
                line = self._process_create_view_line(line)
                stripped_line = line.strip()

            if not self.inside_columns and stripped_line.rstrip().endswith('('):
                # If the CREATE TABLE line ends with '(', move '(' to a new line.
                self.inside_columns = True
                self.first_column = True # Reset for new table definition

                # Find the position of '(' and split the line
                paren_pos = line.rfind('(')
                create_line_part = line[:paren_pos].rstrip()
                indent = line[:len(line) - len(line.lstrip())]

                transformed_lines.append(create_line_part)
                transformed_lines.append(indent + '(')
                continue

            if self.inside_columns and stripped_line.startswith(')'):
                self.inside_columns = False
                transformed_lines.append(line)
                continue

            if self.inside_columns and stripped_line: # Process non-empty lines
                line = re.sub(r',\s*$', '', line)

                if self.first_column:
                    transformed_lines.append(line)
                    self.first_column = False
                else:
                    stripped = line.lstrip()
                    indent = line[:len(line) - len(stripped)]
                    line = f"{indent},{stripped}"
                    transformed_lines.append(line)
            else:
                transformed_lines.append(line)

        return '\n'.join(transformed_lines)

def move_commas_to_start(ddl: str) -> str:
    """Helper function to instantiate and use the DDLFormatter class."""
    formatter = DDLFormatter()
    return formatter.move_commas_to_start(ddl)

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

# GUI with menu bar and split screen
def launch_gui():
    root = tk.Tk()
    root.title("DDL Formatter - Move Commas to Start")
    root.geometry("1400x800")  # Set a default window size
    root.configure(bg="#f0f0f0")

    heading_font = ("Segoe UI", 16, "bold")
    font_style = ("Segoe UI", 14)

    # Menu bar
    menubar = tk.Menu(root)

    def update_status(message, duration=4000):
        status_bar.config(text=message)
        if duration:
            status_bar.after(duration, lambda: status_bar.config(text="Ready"))

    def convert_string():
        ddl = text_input.get("1.0", tk.END).strip()
        if not ddl:
            messagebox.showerror("Error", "Please enter DDL text.")
            return
        transformed = move_commas_to_start(ddl)
        text_output.delete("1.0", tk.END)
        text_output.insert(tk.END, transformed)
        update_status("DDL converted successfully.")

    def clear_text_areas():
        text_input.delete("1.0", tk.END)
        text_output.delete("1.0", tk.END)

    def save_output():
        output_file = filedialog.asksaveasfilename(defaultextension=".sql", filetypes=[("SQL Files", "*.sql")])
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text_output.get("1.0", tk.END))
            update_status(f"Output saved to {os.path.basename(output_file)}")

    def copy_output():
        root.clipboard_clear()
        root.clipboard_append(text_output.get("1.0", tk.END))
        root.update()
        update_status("Output copied to clipboard.")

    def browse_file():
        input_file = filedialog.askopenfilename(filetypes=[("SQL Files", "*.sql")])
        if input_file:
            transformed = process_file(input_file)
            text_output.delete("1.0", tk.END)
            text_output.insert(tk.END, transformed)
            update_status(f"Loaded and converted file: {os.path.basename(input_file)}")

    def browse_folder():
        input_folder = filedialog.askdirectory(title="Select Input Folder")
        if not input_folder:
            return
        output_folder = filedialog.askdirectory(title="Select Output Folder")
        if not output_folder:
            return

        last_input_content = ""
        last_output_content = ""
        file_count = 0

        for filename in os.listdir(input_folder):
            if filename.lower().endswith('.sql'):
                input_path = os.path.join(input_folder, filename)
                with open(input_path, 'r', encoding='utf-8') as f:
                    last_input_content = f.read()
                last_output_content = process_file(input_path)
                output_path = os.path.join(output_folder, filename.replace('.sql', '_formatted.sql'))
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(last_output_content)
                file_count += 1

        if file_count > 0:
            text_input.delete("1.0", tk.END)
            text_input.insert(tk.END, last_input_content)
            text_output.delete("1.0", tk.END)
            text_output.insert(tk.END, last_output_content)
            messagebox.showinfo("Success", f"Processed {file_count} .sql file(s) and saved to {output_folder}.\nShowing the last processed file.")
        else:
            messagebox.showinfo("Information", "No .sql files found in the selected input folder.")

    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Browse File", command=browse_file)
    file_menu.add_command(label="Browse Folder", command=browse_folder)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.destroy)
    menubar.add_cascade(label="File", menu=file_menu)

    # Actions menu
    actions_menu = tk.Menu(menubar, tearoff=0)
    actions_menu.add_command(label="Save Output", command=save_output)
    actions_menu.add_command(label="Copy Output", command=copy_output)
    menubar.add_cascade(label="Actions", menu=actions_menu)

    root.config(menu=menubar)

    # Status bar at the very bottom
    status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W, font=("Segoe UI", 10))
    status_bar.pack(side="bottom", fill="x")

    # Frame for buttons below the text areas, packed first to reserve space at the bottom
    button_frame = tk.Frame(root, bg="#f0f0f0")
    button_frame.pack(side="bottom", fill="x", pady=(5, 10))

    convert_button = tk.Button(button_frame, text="Convert", command=convert_string, font=("Segoe UI", 12, "bold"), bg="#4CAF50", fg="white", padx=10, pady=5)
    clear_button = tk.Button(button_frame, text="Clear", command=clear_text_areas, font=("Segoe UI", 12), padx=10, pady=5)

    # Use grid within the button_frame to center the buttons
    button_frame.grid_columnconfigure(0, weight=1) # Spacer column on the left
    convert_button.grid(row=0, column=1, padx=5)
    clear_button.grid(row=0, column=2, padx=5)
    button_frame.grid_columnconfigure(3, weight=1) # Spacer column on the right

    # Split screen for input and output
    main_frame = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg="#f0f0f0")
    main_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

    input_frame = tk.LabelFrame(main_frame, text="Input DDL", font=heading_font, padx=20, pady=20, bg="#f0f0f0")
    main_frame.add(input_frame, width=700) # Add to paned window with an initial width

    text_input = scrolledtext.ScrolledText(input_frame, width=90, height=40, font=font_style)
    text_input.pack(fill="both", expand=True)
    output_frame = tk.LabelFrame(main_frame, text="Converted DDL", font=heading_font, padx=20, pady=20, bg="#f0f0f0")
    main_frame.add(output_frame)

    text_output = scrolledtext.ScrolledText(output_frame, width=90, height=40, font=font_style)
    text_output.pack(fill="both", expand=True)

    root.mainloop()

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
