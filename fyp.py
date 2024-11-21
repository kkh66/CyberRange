import tkinter as tk
import subprocess
import os
import logging
from tkinter import messagebox, filedialog


logging.basicConfig(
    format='%(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class NotepadManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.index = 0
        self.paragraphs = self.load_instructions()
        self.process = None
        logger.info("Progress: 0")

    def load_instructions(self):
        with open(self.filepath, 'r') as file:
            content = file.read()
            return [p for p in content.split('\n\n') if p.strip()]

    def create_notepad(self):
        self.update_notepad()

    def update_notepad(self):
        if self.process:
            self.process.terminate()
        with open('tut.txt', 'w') as file:
            file.write(self.paragraphs[self.index].strip())
        self.process = subprocess.Popen(['gedit', 'tut.txt'])

    def next_paragraph(self):
        if self.index < len(self.paragraphs) - 1:
            self.index += 1
            self.update_notepad()
            return True
        return False

    def previous_paragraph(self):
        if self.index > 0:
            self.index -= 1
            self.update_notepad()
            return True
        return False

    def reset(self):
        self.index = 0
        logger.info("Progress: 0")


class PercentageWindow(tk.Toplevel):
    def __init__(self):
        super().__init__()
        self.title("Progress Percentage")
        self.geometry("200x100")
        self.label = tk.Label(self, text="0%")
        self.label.pack(pady=20)
        self.percentage = 0

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_percentage(self, increment=5):
        if self.percentage < 100:
            self.percentage += increment
            if self.percentage > 100:
                self.percentage = 100
            self.label.config(text=f"{self.percentage}%")
            
            logger.info(f"Progress: {int(self.percentage)}")

    def decrease_percentage(self, decrement=5):
        if self.percentage > 0:
            self.percentage -= decrement
            self.label.config(text=f"{self.percentage}%")
            
            logger.info(f"Progress: {int(self.percentage)}")

    def reset(self):
        self.percentage = 0
        self.label.config(text="0%")
        logger.info("Progress: 0")

    def on_close(self):
        if self.percentage < 100:
            messagebox.showwarning("Warning", "You cannot close this window until the percentage is 100%")
        else:
            logger.info("Progress: 100")
            self.destroy()


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instruction Viewer")
        self.geometry("300x300")

        self.label = tk.Label(self, text="Choose your level:")
        self.label.pack(pady=20)

        self.beginner_button = tk.Button(self, text="Beginner", command=self.start_beginner)
        self.beginner_button.pack(pady=5)

        self.advanced_button = tk.Button(self, text="Advanced", command=self.start_advanced)
        self.advanced_button.pack(pady=5)

        self.forward_button = tk.Button(self, text="Forward", command=self.forward)
        self.forward_button.pack(pady=5)

        self.back_button = tk.Button(self, text="Back", command=self.back)
        self.back_button.pack(pady=5)

        self.notepad_manager = None
        self.percentage_window = PercentageWindow()

        # Override close event
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def find_instruction_file(self, filename):
        # Check if the file exists in /home/kali/
        home_path = "/config/Desktop/"
        file_path = os.path.join(home_path, filename)

        if os.path.exists(file_path):
            return file_path
        else:
            # If the file is not found, allow the user to select a file
            file_path = filedialog.askopenfilename(title=f"Select {filename}", initialdir=home_path, filetypes=(("Text files", "*.txt"),))
            if not file_path:
                messagebox.showerror("File Not Found", f"{filename} was not found in {home_path} and no file was selected.")
                return None
            return file_path

    def start_beginner(self):
        instruction_file = self.find_instruction_file("beginnerInstruction.txt")
        if instruction_file:
            logger.info("Level: Beginner")
            self.start_instruction(instruction_file, increment=10)

    def start_advanced(self):
        instruction_file = self.find_instruction_file("advancedInstruction.txt")
        if instruction_file:
            logger.info("Level: Advanced")
            self.start_instruction(instruction_file, increment=20)

    def start_instruction(self, filename, increment):
        try:
            self.beginner_button.config(state=tk.DISABLED)
            self.advanced_button.config(state=tk.DISABLED)

            self.notepad_manager = NotepadManager(filename)
            self.notepad_manager.create_notepad()
            self.percentage_window.reset()
            
            
            logger.info(f"Progress: 0")

        except Exception as e:
            logger.error(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to start instructions: {str(e)}")

    def forward(self):
        if self.notepad_manager:
            if self.notepad_manager.next_paragraph():
                increment = 9.1 if self.notepad_manager.filepath.endswith("advancedInstruction.txt") else 7
                self.percentage_window.update_percentage(increment)

            if self.percentage_window.percentage == 100:
                self.on_instruction_complete()

    def back(self):
        if self.notepad_manager:
            if self.notepad_manager.previous_paragraph():
                decrement = 9.1 if self.notepad_manager.filepath.endswith("advancedInstruction.txt") else 7
                self.percentage_window.decrease_percentage(decrement)

    def on_instruction_complete(self):
        logger.info("Progress: 100")
        messagebox.showinfo("Completion", "You have completed the instructions!")
        self.beginner_button.config(state=tk.NORMAL)
        self.advanced_button.config(state=tk.NORMAL)

    def on_close(self):
        if self.percentage_window.percentage < 100:
            messagebox.showwarning("Warning", "You cannot close this window until the percentage is 100%")
        else:
            self.percentage_window.destroy()
            self.destroy()


if __name__ == "__main__":
    app = Application()
    app.mainloop()
