"""No-API ChatGPT cinematic handoff and local face compositing."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from identity_compositor import process

PROMPT = """Edit the ATTACHED PHOTO, preserving the exact original composition, camera angle,
perspective, framing, crop, pose, anatomy, object count, clothing, and positions.
Do NOT redraw, replace, beautify, morph, or alter any face or facial features,
expression, skin texture, hands, fingers, limbs, or body shape. Do not add or
remove people or objects. Keep the same pixel dimensions and subject positions.
Transform ONLY the photographic mood: premium cinematic wedding editorial,
warm natural golden-hour color grading, dimensional light, subtle atmospheric
glow, controlled highlights, rich but believable shadows, pleasing skin tones,
and refined background color. Avoid excessive sharpening, plastic skin, fake
bokeh, or invented light sources. Prefer a restrained, photorealistic edit.
Maintain spatial alignment with the original so that original faces can be
composited back afterwards. If exact preservation is uncertain, leave the
relevant area unchanged. This is photo editing, NOT scene recreation."""

def main():
    root = tk.Tk()
    root.title("AI RAW Editor — Cinematic Handoff")
    root.geometry("700x470")
    paths = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
    ttk.Label(root, text="Creative Cinematic — ChatGPT manual workflow", font=("Segoe UI", 14, "bold")).pack(pady=14)
    for i, label in enumerate(("Original photo (JPEG/PNG)", "ChatGPT cinematic result", "Save final composite")):
        frame = ttk.Frame(root); frame.pack(fill="x", padx=20, pady=6)
        ttk.Label(frame, text=label, width=25).pack(side="left")
        ttk.Entry(frame, textvariable=paths[i]).pack(side="left", fill="x", expand=True, padx=5)
        def choose(index=i):
            value = (filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG", "*.jpg")])
                     if index==2 else filedialog.askopenfilename(filetypes=[("Images","*.jpg *.jpeg *.png")]))
            if value: paths[index].set(value)
        ttk.Button(frame, text="Browse", command=choose).pack(side="right")
    def copy_prompt():
        root.clipboard_clear(); root.clipboard_append(PROMPT); root.update()
        messagebox.showinfo("Prompt copied", "Paste into ChatGPT with your original photo.")
    ttk.Button(root, text="1. Copy cinematic prompt for ChatGPT", command=copy_prompt).pack(pady=12)
    ttk.Label(root, text="2. Generate in ChatGPT and save the image. 3. Select both images above.").pack()
    def run():
        try:
            if not all(p.get() for p in paths): raise ValueError("Select original, generated and output paths")
            report = process(*(p.get() for p in paths))
            messagebox.showinfo("Saved", f"Saved protected composite. Faces processed: {len(report)}. Inspect at 100% zoom.")
        except Exception as exc:
            messagebox.showerror("Safe stop", str(exc))
    ttk.Button(root, text="3. Restore original faces & save", command=run).pack(pady=15)
    ttk.Label(root, text="Safety: stops on missing faces, changed dimensions or major face displacement.\n"
             "Face detection is imperfect; always visually inspect before delivery.", justify="center").pack()
    root.mainloop()

if __name__ == "__main__":
    main()
