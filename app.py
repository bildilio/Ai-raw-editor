"""AI RAW Editor desktop UI."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from editor import PRESETS, Settings, export_batch

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('AI RAW Editor — You shoot. AI edits. You approve.')
        self.geometry('740x460')
        self.source = tk.StringVar()
        self.output = tk.StringVar()
        self.preset = tk.StringVar(value='Natural')
        self.strength = tk.DoubleVar(value=.75)
        self.status = tk.StringVar(value='Select your RAW folder to begin')
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        frame = ttk.Frame(self, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='AI RAW Editor', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='You shoot. AI edits. You approve. | Adaptive editing MVP').pack(anchor='w', pady=(0, 15))
        for title, var, callback in [('RAW photo folder', self.source, self.choose_source),
                                     ('JPEG export folder', self.output, self.choose_output)]:
            ttk.Label(frame, text=title).pack(anchor='w', pady=(8, 2))
            row = ttk.Frame(frame)
            row.pack(fill='x')
            ttk.Entry(row, textvariable=var).pack(side='left', fill='x', expand=True)
            ttk.Button(row, text='Browse', command=callback).pack(side='left', padx=6)
        ttk.Label(frame, text='Editing look').pack(anchor='w', pady=(12, 3))
        ttk.Combobox(frame, textvariable=self.preset, values=list(PRESETS), state='readonly').pack(fill='x')
        ttk.Label(frame, text='Edit strength').pack(anchor='w', pady=(12, 3))
        ttk.Scale(frame, from_=0, to=1, variable=self.strength).pack(fill='x')
        controls = ttk.Frame(frame)
        controls.pack(fill='x', pady=14)
        self.start = ttk.Button(controls, text='Auto Edit & Export', command=self.run)
        self.start.pack(side='left')
        ttk.Button(controls, text='Cancel', command=self.cancel.set).pack(side='left', padx=10)
        ttk.Label(frame, textvariable=self.status, wraplength=670).pack(anchor='w')
        self.after(150, self.poll)

    def choose_source(self):
        value = filedialog.askdirectory(title='Select RAW source folder')
        if value:
            self.source.set(value)

    def choose_output(self):
        value = filedialog.askdirectory(title='Select JPEG output folder')
        if value:
            self.output.set(value)

    def run(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.source.get() or not self.output.get():
            messagebox.showwarning('Missing folder', 'Select source and export folders')
            return
        settings = Settings(self.preset.get(), self.strength.get())
        self.cancel.clear()
        self.start.configure(state='disabled')
        self.status.set('Processing photos...')
        def work():
            try:
                report = export_batch(self.source.get(), self.output.get(), settings,
                    notify=lambda i, total, path: self.events.put(('progress', f'{i}/{total}: {path}')),
                    cancelled=self.cancel)
                successes = sum(item['status'] == 'ok' for item in report)
                self.events.put(('done', f'Finished: {successes}/{len(report)} photos. See edit_report.csv'))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                self.status.set(value)
                if kind in ('done', 'error'):
                    self.start.configure(state='normal')
                    if kind == 'error':
                        messagebox.showerror('Editing failed', value)
        except queue.Empty:
            pass
        self.after(150, self.poll)

if __name__ == '__main__':
    App().mainloop()
