
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import subprocess
import re
import time
from datetime import timedelta
import signal



# Command terminal arguments are specified in the class batch_process
class batch_process:
    def __init__(self, tasks, venv_activate, progress_callback=None, status_callback=None):
        self.tasks = tasks
        self.venv_activate = venv_activate
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.process = None  

    def run(self):
        for i, task in enumerate(self.tasks, start=1):
            # self.process = subprocess.Popen(...)

            input_path = task['input']
            imaris_path = task['imaris']
            if self.status_callback:
                self.status_callback(f"Running Task {i}")
            command = (
                f"source ~/anaconda3/etc/profile.d/conda.sh && "
                f"conda activate stitching && "
                f"python3 convert.py "
                f"--input \"{input_path}\" "
                f"--imaris \"{imaris_path}\" "
                f"-dx 0.71 -dy 0.71 -dz 0.71"
            )
            self.process = subprocess.Popen(command, shell=True, executable="/bin/bash",
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            progress_pattern = re.compile(r"IMS:\s+(\d+(\.\d+)?)%")
            start_time = time.time()
            last_percent = -1
            for line in self.process.stdout:
                match = progress_pattern.search(line)
                if match:
                    percent = float(match.group(1))
                    if int(percent) != int(last_percent):
                        last_percent = percent
                        self.update_progress_bar(percent, start_time)
            self.process.wait()
            self.update_progress_bar(100, start_time)
            if self.process.returncode == 0 and self.status_callback:
                self.status_callback(f"✅ Task {i} completed successfully.")
            elif self.status_callback:
                self.status_callback(f"❌ Task {i} failed.")

    def update_progress_bar(self, percent, start_time):
        elapsed = time.time() - start_time
        estimated_total = (elapsed / percent) * 100 if percent > 0 else 0
        eta = estimated_total - elapsed
        if self.progress_callback:
            self.progress_callback(percent, elapsed, eta, estimated_total)

    

    def pause(self):
        if self.process:
            self.process.send_signal(signal.SIGSTOP)

    def resume(self):
        if self.process:
            self.process.send_signal(signal.SIGCONT)

    def stop(self):
        if self.process:
            self.process.terminate()

# GUI app with tabs
class ConversionGUI:
    def __init__(self, root):
        self.root = root
        root.title("Imaris Conversion GUI")

        self.task_list = []

        notebook = ttk.Notebook(root)
        notebook.pack(expand=True, fill='both')

        self.single_tab = ttk.Frame(notebook)
        self.queue_tab = ttk.Frame(notebook)

        notebook.add(self.single_tab, text="Single Task")
        notebook.add(self.queue_tab, text="Task Queue")

        self.build_single_tab()
        self.build_queue_tab()

    def build_single_tab(self):
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()

        tk.Label(self.single_tab, text="Input Folder:").pack(pady=2)
        tk.Entry(self.single_tab, textvariable=self.input_path, width=60).pack(pady=2)
        tk.Button(self.single_tab, text="Browse", command=self.browse_input).pack(pady=2)

        tk.Label(self.single_tab, text="Output .ims File:").pack(pady=2)
        tk.Entry(self.single_tab, textvariable=self.output_path, width=60).pack(pady=2)
        tk.Button(self.single_tab, text="Browse", command=self.browse_output).pack(pady=2)




        self.progress = ttk.Progressbar(self.single_tab, length=400, mode='determinate')
        self.progress.pack(pady=10)
        self.progress_info = tk.Label(self.single_tab, text="Progress: 0.0%")
        self.progress_info.pack()
        self.status = tk.Label(self.single_tab, text="")
        self.status.pack(pady=5)
        # tk.Button(self.single_tab, text="Start", command=self.start_single_agent).pack(pady=10)

        btn_frame = tk.Frame(self.single_tab)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Start", command=self.start_single_agent).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Pause", command=self.pause_agent).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Resume", command=self.resume_agent).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Stop", command=self.stop_agent).pack(side='left', padx=5)

    def build_queue_tab(self):
        self.tree = ttk.Treeview(self.queue_tab, columns=("Input", "Output"), show='headings')
        self.tree.heading("Input", text="Input Folder")
        self.tree.heading("Output", text="Output .ims File")
        self.tree.pack(expand=True, fill='both', pady=5)

        tk.Button(self.queue_tab, text="Add Task", command=self.add_task).pack(pady=2)
        tk.Button(self.queue_tab, text="Clear Queue", command=self.clear_queue).pack(pady=2)
        tk.Button(self.queue_tab, text="Run Queue", command=self.run_queue_agent).pack(pady=5)

    def browse_input(self):
        path = filedialog.askdirectory()
        self.input_path.set(path)

    def browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".ims")
        self.output_path.set(path)

    def update_progress_bar(self, percent, elapsed, eta, total):
        self.progress['value'] = percent
        self.progress_info.config(
            text=f"Progress: {percent:.1f}% | Elapsed: {self.format_time(elapsed)} | ETA: {self.format_time(eta)} | Total: ~{self.format_time(total)}"
        )
        self.root.update_idletasks()

    def update_status(self, message):
        self.status.config(text=message)

    def start_single_agent(self):
        task = {"input": self.input_path.get(), "imaris": self.output_path.get()}
        
        venv_activate = (
        "source ~/anaconda3/etc/profile.d/conda.sh && "
        "conda activate stitching")
        self.active_agent = batch_process([task], venv_activate,
                                   progress_callback=self.update_progress_bar,
                                   status_callback=self.update_status)

        threading.Thread(target=self.active_agent.run, daemon=True).start()


    def pause_agent(self):
        if hasattr(self, 'active_agent'):
            self.active_agent.pause()
            self.update_status("⏸ Paused")

    def resume_agent(self):
        if hasattr(self, 'active_agent'):
            self.active_agent.resume()
            self.update_status("▶ Resumed")

    def stop_agent(self):
        if hasattr(self, 'active_agent'):
            self.active_agent.stop()
            self.update_status("⏹ Stopped")




    def add_task(self):
        input_path = filedialog.askdirectory()
        output_path = filedialog.asksaveasfilename(defaultextension=".ims")
        if input_path and output_path:
            self.task_list.append({"input": input_path, "imaris": output_path})
            self.tree.insert("", "end", values=(input_path, output_path))

    def clear_queue(self):
        self.tree.delete(*self.tree.get_children())
        self.task_list.clear()

    def run_queue_agent(self):
        if not self.task_list:
            messagebox.showwarning("Empty Queue", "Add tasks before running.")
            return
        venv_activate = (
        "source ~/anaconda3/etc/profile.d/conda.sh && "
        "conda activate stitching")
        agent = batch_process(self.task_list, venv_activate,
                               progress_callback=self.update_progress_bar,
                               status_callback=self.update_status)
        threading.Thread(target=agent.run, daemon=True).start()

    @staticmethod
    def format_time(seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02}:{m:02}:{s:02}"

if __name__ == "__main__":
    root = tk.Tk()
    app = ConversionGUI(root)
    root.mainloop()
