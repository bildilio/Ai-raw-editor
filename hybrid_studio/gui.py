"""Windows-friendly local GUI for Hybrid Identity Studio."""
from __future__ import annotations
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

from . import engine


class Studio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Hybrid Identity Studio — AI RAW Editor')
        self.geometry('1080x820')
        self.minsize(770,620)
        self.original = tk.StringVar()
        self.generated = tk.StringVar()
        self.strength = tk.DoubleVar(value=.90)
        self.status = tk.StringVar(value='Pilih foto asli dan hasil generatif dari ChatGPT')
        self.events = queue.Queue()
        self.result = None
        self.mask = None
        self.base = None
        self.photo_ref = None
        self.worker = None
        self.render_mask = tk.BooleanVar(value=False)
        self._build()
        self.after(120,self._poll)

    def _build(self):
        root=ttk.Frame(self,padding=16)
        root.pack(fill='both',expand=True)
        ttk.Label(root,text='Hybrid Identity Studio',font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(root,text='Generative-first · wajah asli · relighting mengikuti AI · tanpa API').pack(anchor='w',pady=(0,12))
        for label,var in [('Foto asli',self.original),('Hasil generative AI (simpan dari ChatGPT)',self.generated)]:
            ttk.Label(root,text=label).pack(anchor='w')
            row=ttk.Frame(root);row.pack(fill='x',pady=(3,9))
            ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True)
            ttk.Button(row,text='Pilih...',command=lambda v=var:self._pick(v)).pack(side='left',padx=5)
        ttk.Label(root,text='Kekuatan mengikuti pencahayaan AI').pack(anchor='w')
        ttk.Scale(root,from_=0,to=1,variable=self.strength).pack(fill='x',pady=(2,7))
        bar=ttk.Frame(root);bar.pack(fill='x',pady=(4,7))
        ttk.Button(bar,text='Unduh model deteksi wajah (sekali)',command=self._download).pack(side='left')
        self.go=ttk.Button(bar,text='Proses & Preview',command=self._process)
        self.go.pack(side='left',padx=8)
        self.save_button=ttk.Button(bar,text='Ekspor foto final...',command=self._save,state='disabled')
        self.save_button.pack(side='left')
        ttk.Checkbutton(bar,text='Tampilkan area masker',variable=self.render_mask,command=self._render).pack(side='left',padx=8)
        ttk.Label(root,textvariable=self.status,wraplength=970).pack(anchor='w',pady=8)
        preview_holder=ttk.Frame(root)
        preview_holder.pack(fill='both',expand=True)
        self.preview=ttk.Label(preview_holder,text='Pratinjau hasil muncul di sini',anchor='center')
        self.preview.pack(fill='both',expand=True)
        ttk.Label(root,text='WAJIB periksa zoom 100% pada wajah & batas hijab sebelum ekspor. Jika gagal deteksi, aplikasi menolak hasil otomatis.',
                  wraplength=980).pack(anchor='w',pady=(7,0))

    def _pick(self,var):
        file=filedialog.askopenfilename(filetypes=[('Foto','*.jpg *.jpeg *.png *.webp *.tif *.tiff'),('Semua','*.*')])
        if file:
            var.set(file)
            self.result=None
            self.save_button.configure(state='disabled')

    def _thread(self,action):
        if self.worker and self.worker.is_alive():return
        self.go.configure(state='disabled')
        self.worker=threading.Thread(target=action,daemon=True)
        self.worker.start()

    def _download(self):
        self.status.set('Mengunduh model MediaPipe resmi (hanya sekali)...')
        def action():
            try:self.events.put(('status',f'Model tersedia: {engine.ensure_model(download=True)}'))
            except Exception as e:self.events.put(('error',str(e)))
            finally:self.events.put(('ready',None))
        self._thread(action)

    def _process(self):
        if not Path(self.original.get()).is_file() or not Path(self.generated.get()).is_file():
            messagebox.showwarning('Foto belum dipilih','Pilih foto asli dan hasil generatif terlebih dahulu')
            return
        self.status.set('Memeriksa landmark kedua foto dan menyelaraskan wajah...')
        self.result=None
        self.save_button.configure(state='disabled')
        def action():
            try:
                source=engine.load_rgb(self.original.get())
                generated=engine.load_rgb(self.generated.get())
                result,mask,reports=engine.composite(source,generated,strength=self.strength.get())
                # Preview uses generated resized to input size after aspect check.
                if generated.shape!=source.shape:
                    import cv2
                    generated=cv2.resize(generated,(source.shape[1],source.shape[0]))
                self.events.put(('result',(result,mask,generated,reports)))
            except Exception as e:self.events.put(('error',str(e)))
            finally:self.events.put(('ready',None))
        self._thread(action)

    def _poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='error':
                    self.status.set('GAGAL AMAN: '+value)
                    messagebox.showerror('Compositing ditolak',value)
                elif kind=='status':self.status.set(value)
                elif kind=='ready':self.go.configure(state='normal')
                elif kind=='result':
                    self.result,self.mask,self.base,reports=value
                    self.status.set(f'{len(reports)} wajah diselaraskan. Periksa preview; ekspor hanya jika identitas dan blending terlihat benar.')
                    self.save_button.configure(state='normal')
                    self._render()
        except queue.Empty:pass
        self.after(120,self._poll)

    def _render(self):
        if self.result is None:return
        img=self.result if not self.render_mask.get() else engine.mask_preview(self.base,self.mask)
        w=max(self.preview.winfo_width()-12,440)
        h=max(self.preview.winfo_height()-12,320)
        im=Image.fromarray(img)
        im.thumbnail((w,h),Image.Resampling.LANCZOS)
        self.photo_ref=ImageTk.PhotoImage(im)
        self.preview.configure(image=self.photo_ref,text='')

    def _save(self):
        if self.result is None:return
        if not messagebox.askyesno('Verifikasi manusia','Sudah periksa detail wajah dan masker? Ekspor hasil ini?'):
            return
        name=Path(self.original.get()).stem+'_hybrid_identity.jpg'
        dst=filedialog.asksaveasfilename(defaultextension='.jpg',initialfile=name,
             filetypes=[('JPEG','*.jpg'),('PNG','*.png')])
        if dst:
            engine.save_rgb(self.result,dst)
            mask_path=str(Path(dst).with_name(Path(dst).stem+'_mask.png'))
            engine.save_rgb(engine.mask_preview(self.base,self.mask),mask_path)
            self.status.set(f'Hasil: {dst} | Diagnostic mask: {mask_path}')


def main():
    Studio().mainloop()
