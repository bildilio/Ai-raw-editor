# AI RAW Editor

**You shoot. AI edits. You approve.**

A photographer-first Windows RAW editing application. The current **MVP** performs local, non-generative adaptive color and tonal adjustments, batch exports JPEGs, and never modifies the original RAW files. It is **not yet** a trained AI retoucher.

## Run locally
Requires Windows and Python 3.11:
```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Build portable Windows EXE
GitHub Actions → **Build Windows App** → Run workflow → download the build artifact.

## Current scope
- RAW decoding via rawpy/LibRaw (camera support varies)
- Per-photo adaptive exposure/contrast/saturation
- Natural, Wedding Soft, Moody, Bright Editorial styles
- Batch JPEG output; source files remain untouched

## Planned professional AI editor
Subject-aware masks, face/skin retouching, reference-matched color grading, before/after review, non-destructive edit recipe, quality checks and photographer approval. These are planned, not implemented.

For professional delivery, review colors and highlights before exporting. No cloud upload or generative image replacement in the MVP.
