# Hybrid Identity Studio — modul AI RAW Editor

**Tujuan:** pakai foto hasil generative AI ChatGPT sebagai lapisan dasar, pertahankan **piksel/detail wajah dari foto asli**, dan adaptasikan pencahayaan wajah ke hasil generatif tanpa API berbayar. Pemrosesan foto dilakukan lokal di PC.

## Instalasi Windows (Python 3.11)

```powershell
git clone https://github.com/bildilio/Ai-raw-editor.git
cd Ai-raw-editor
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-hybrid.txt
python -m hybrid_studio
```

Jika PowerShell memblokir aktivasi, jalankan langsung `.venv\Scripts\python.exe -m hybrid_studio` (atau gunakan `Set-ExecutionPolicy -Scope Process Bypass`).

## Penggunaan

1. Di ChatGPT, unggah foto asli dan minta *generative cinematic edit* dengan pose dan komposisi sedekat mungkin dengan foto asli. Simpan hasil JPG/PNG-nya.
2. Buka aplikasi dan klik **Unduh model deteksi wajah** saat pertama kali (model resmi MediaPipe ~3–4 MB). Foto tidak diunggah saat proses.
3. Pilih `Foto asli` dan `Hasil generative AI`.
4. Klik **Proses & Preview**. Lihat masker melalui checkbox, cek kedua wajah pada zoom 100% di file hasil.
5. Jika sesuai, klik **Ekspor foto final**. Hasil dan preview masker disimpan sebagai file lokal.

## Desain

- Generated image = keseluruhan foto utama.
- MediaPipe Face Landmarker Tasks API (bukan `mp.solutions` lama) mendeteksi 478 titik wajah.
- Pencocokan wajah berdasarkan posisi/ukuran, **bukan pengenalan identitas**.
- Affine similarity terbatas untuk alignment. Wajah dengan perubahan besar/pose berbeda ditolak; tidak dipaksa menempel.
- Polygon kontur muka dari landmark, erosi ke dalam, feathering sempit agar background tidak ikut terangkat.
- Luminance/chroma wajah meniru referensi generatif melalui LAB low-frequency transfer, sedangkan microtexture tetap dari foto asli.
- Foto sumber tak pernah diubah. Ekspor hanya setelah review pengguna.

## Batasan penting

Versi ini **MVP**, belum jaminan pixel-perfect atau identitas 100%. Jika ChatGPT meregenerasi pose, sudut pandang, bentuk kepala, atau ekspresi secara ekstrem, otomatisasi akan gagal tertutup. Rambut/hijab/tangan/pakaian bukan dikunci secara fisik; bagian tersebut berasal dari gambar generatif sehingga masih dapat berubah. Untuk dokumen resmi atau foto penting, periksa wajah, pakaian, dan komposisi secara visual. Tidak ada fitur menggambar polygon manual atau penggabungan 3D tingkat lanjut di versi awal. Masker wajah meliputi kontur wajah bagian dalam dan mungkin tidak melindungi tepian hijab. Untuk subjek sangat kecil/blur, landmark dapat gagal.

Aplikasi ini **tidak mengakses akun ChatGPT** dan **tidak menghasilkan gambar generatif**. ChatGPT Plus tidak menyediakan API gambar gratis; input generatif tetap diunduh manual dari ChatGPT.

## Debug

- `Deteksi wajah tidak cocok`: ulangi generative edit dengan wajah/pose tidak bergeser dan tanpa orang tambahan.
- `Rasio gambar berbeda`: crop foto generatif ke aspek rasio asli sebelum diproses.
- `Geometri wajah tidak kompatibel`: hasil AI mengganti pose/ekspresi terlalu jauh; lakukan generative edit lain dengan instruksi lebih ketat.
- Wajah terlalu gelap/terang: sesuaikan slider *Kekuatan mengikuti pencahayaan AI*, lalu bandingkan preview.
