import tkinter as tk
from tkinter import ttk
import configparser
import os
import subprocess
import threading


class PixivDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixiv Downloader GUI")
        self.root.geometry("1200x700")

        self.config = configparser.ConfigParser()
        self.config_path = "config.ini"
        self.config_exists = self.load_config()

        self.create_widgets()

        # Event to signal thread completion
        self.thread_complete_event = threading.Event()

    def load_config(self):
        """Load the configuration if the config file exists, or set config_exists to False."""
        self.config.clear()  # Clear any old config data
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config.read_file(f)
                return True
            except UnicodeDecodeError as e:
                print(f"Error reading config file: {e}")
                return False
        else:
            return False

    def create_widgets(self):
        self.tabs = ttk.Notebook(self.root)

        # Always add home tab first
        self.tab_home = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_home, text="Home")
        self.tabs.pack(expand=1, fill="both")

        # Init the home tab
        self.init_home_tab()

    def init_home_tab(self):
        # Configure the grid to center the contents
        self.tab_home.grid_columnconfigure(0, weight=1)  # Center column 0
        self.tab_home.grid_columnconfigure(1, weight=1)  # Center column 1

        # Welcome label
        tk.Label(self.tab_home, text="Welcome to Pixiv Downloader", font=("Arial", 16)).grid(
            row=0, column=0, columnspan=2, pady=20, sticky="n"
        )

        # Username field
        tk.Label(self.tab_home, text="Username:").grid(row=1, column=0, sticky="e", padx=10, pady=5)
        self.username_entry = tk.Entry(self.tab_home, width=50, state="readonly")
        self.username_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # Password field
        tk.Label(self.tab_home, text="Password:").grid(row=2, column=0, sticky="e", padx=10, pady=5)
        self.password_entry = tk.Entry(self.tab_home, width=50, state="readonly", show="*")
        self.password_entry.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        # Cookie field
        tk.Label(self.tab_home, text="Cookie:").grid(row=3, column=0, sticky="e", padx=10, pady=5)
        self.cookie_entry = tk.Entry(self.tab_home, width=50, state="readonly")
        self.cookie_entry.grid(row=3, column=1, sticky="w", padx=10, pady=5)

        # Continue button (renamed to "Test")
        self.continue_button = tk.Button(self.tab_home, text="Test", command=self.show_all_tabs)
        self.continue_button.grid(row=4, column=0, pady=20, sticky="e", padx=5)

        # Reload button
        self.reload_button = tk.Button(self.tab_home, text="Reload", command=self.reload_fields)
        self.reload_button.grid(row=4, column=1, pady=20, sticky="w", padx=5)

        # Set values after all entries are defined
        self.set_entry_value(self.username_entry, 'username')
        self.set_entry_value(self.password_entry, 'password')
        self.set_entry_value(self.cookie_entry, 'cookie')

        # Update Continue button based on field values
        self.update_continue_button()

    def reload_fields(self):
        """Reload the fields by reloading the configuration file."""
        self.config_exists = self.load_config()  # Reload the config file
        self.set_entry_value(self.username_entry, 'username')
        self.set_entry_value(self.password_entry, 'password')
        self.set_entry_value(self.cookie_entry, 'cookie')
        self.update_continue_button()  # Update the Continue button

    def set_entry_value(self, entry_widget, key):
        """Populate entry with value from config or 'Config file does not exist'."""
        if self.config_exists:
            if 'Authentication' in self.config:
                if key in self.config['Authentication']:
                    value = self.config['Authentication'].get(key, '').strip()
                    if value == "":  # Check if the value is an empty string
                        value = "Empty"
                else:
                    value = "Empty"
            else:
                value = "Authentication section missing"
        else:
            value = "Config file does not exist"  # Set value to indicate missing config file

        # Temporarily set the state to 'normal' to allow population
        entry_widget.config(state='normal')

        # Clear any existing value and set the appearance and value
        entry_widget.delete(0, tk.END)
        if value in ["Config file does not exist", "Authentication section missing", "Empty"]:
            entry_widget.insert(0, value)
            entry_widget.config(fg="grey", font=("Arial", 10, "italic", "bold"))
            # Remove asterisks for grey placeholder text in password field
            if entry_widget == self.password_entry:
                entry_widget.config(show="")
        else:
            entry_widget.insert(0, value)
            entry_widget.config(fg="black", font=("Arial", 10, "italic", "bold"))
            # Add asterisks for actual password content
            if entry_widget == self.password_entry:
                entry_widget.config(show="*")

        # Make the field readonly after population
        entry_widget.config(state='readonly')

        # Update Continue button
        self.update_continue_button()

    def update_continue_button(self):
        """Change Continue button to Exit and close the app if fields are grey."""
        if any(
            field.get() in ["Config file does not exist", "Empty"]
            for field in [self.username_entry, self.password_entry, self.cookie_entry]
        ):
            self.continue_button.config(text="Exit", command=self.exit_application)
        else:
            self.continue_button.config(text="Test", command=self.show_all_tabs)

    def exit_application(self):
        """Exit the application."""
        self.root.quit()
        self.root.destroy()

    def show_all_tabs(self):
        """Run PixivUtil2.py and display its output in the GUI."""
        # Create a new frame for the output
        self.output_frame = tk.Frame(self.root)
        self.output_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create a scrollable text widget to display the output
        self.output_text = tk.Text(self.output_frame, wrap="word", state="disabled", height=20, width=100)
        self.output_text.pack(side="left", fill="both", expand=True)

        # Add a vertical scrollbar
        self.scrollbar = ttk.Scrollbar(self.output_frame, orient="vertical", command=self.output_text.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.output_text.config(yscrollcommand=self.scrollbar.set)

        # Add the "Proceed to Options" button (initially disabled)
        self.proceed_button = tk.Button(self.root, text="Proceed to Options", state="disabled", command=self.proceed_to_options)
        self.proceed_button.pack(pady=10)

        # Run PixivUtil2.py in a separate thread
        threading.Thread(target=self.run_pixivutil2_process, daemon=True).start()

        # Use an after call to periodically check if the thread is done
        self.check_thread_complete()

    def check_thread_complete(self):
        """Periodically check if the thread has finished and enable the Proceed button."""
        if self.thread_complete_event.is_set():  # Check if the thread has finished
            self.proceed_button.config(state="normal")  # Enable the button
        else:
            # Check again in 100 milliseconds
            self.root.after(100, self.check_thread_complete)

    def run_pixivutil2_process(self):
        """Run PixivUtil2.py as a subprocess and capture its output."""
        try:
            # Set the environment variable to force UTF-8 encoding
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            # Run PixivUtil2.py and capture its output
            process = subprocess.Popen(
                ["python", "PixivUtil2.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env
            )

            # Read the output line by line
            for line in process.stdout:
                try:
                    decoded_line = line.decode("utf-8", errors="replace").replace("�", "?")
                except Exception as e:
                    decoded_line = f"[Decode error]: {e}\n"
                self.append_output(decoded_line)

                # Check if the options menu is displayed
                if "Input:" in decoded_line:  # Detect the options menu prompt
                    # Append final message after options menu
                    self.append_output("\nOptions menu is ready. You can now proceed.\n")

                    # Enable the "Proceed to Options" button
                    self.root.after(0, lambda: self.proceed_button.config(state="normal"))
                    break

        except Exception as e:
            self.append_output(f"\nError: {e}\n")

    def append_output(self, text):
        """Append text to the output text widget."""
        self.output_text.config(state="normal")  # Enable the text widget for writing
        self.output_text.insert(tk.END, text)  # Insert the text
        self.output_text.see(tk.END)  # Scroll to the end
        self.output_text.config(state="disabled")  # Disable editing

    def proceed_to_options(self):
        """Handle the Proceed to Options button click."""
        self.append_output("\nProceeding to options...\n")
        # Add logic to handle the next steps here


if __name__ == "__main__":
    root = tk.Tk()
    app = PixivDownloaderGUI(root)
    root.mainloop()
