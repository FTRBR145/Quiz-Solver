# 🎯 Auto Quiz Extractor & Solver (Gemini 3.8 Flash)

Program otomasi cerdas berbasis **Python**, **Playwright**, dan **Google Gemini 3.8 Flash** yang dirancang khusus untuk mengekstrak pertanyaan dari website kuis bertahap (soal yang tampil satu per satu dan memerlukan klik tombol **"Next" / "Berikutnya"**), mencari kunci jawaban serta pembahasannya secara realtime, dan merekap seluruh hasil ke dalam format **Markdown (.md)** dan **JSON**.

---

## ✨ Fitur Utama

1. **Dukungan Soal Bertahap (Next Button Detection)**:
   - Mendeteksi dan mengklik tombol navigasi seperti *Next*, *Berikutnya*, *Selanjutnya*, *Lanjut*, *Simpan & Lanjut*, atau ikon panah secara otomatis.
   - Mendeteksi tombol *Selesai / Submit / Kumpulkan* pada nomor terakhir.
2. **Kecerdasan Buatan Gemini 3.8 Flash**:
   - Membedah teks soal, nomor urut, dan opsi pilihan ganda secara terstruktur.
   - Memberikan rekomendasi jawaban terbaik, tingkat keyakinan (*confidence*), serta pembahasan logis yang mendalam.
3. **Dua Mode Operasi Fleksibel**:
   - **Mode Semi-Otomatis (Direkomendasikan)**: Jawaban dan pembahasan tampil di terminal. Anda cukup menekan tombol `[ENTER]` di terminal agar program mengklik tombol Next dan memproses nomor berikutnya. Sangat aman dan terkendali.
   - **Mode Otomatis Penuh**: Program otomatis memilih opsi jawaban di web dan mengklik tombol Next sesuai jeda waktu yang ditentukan.
4. **Sesi Browser Tersimpan (*Persistent Context*)**:
   - Browser terbuka di layar (*headed mode*). Anda dapat login ke akun kuis, mengisi captcha, atau menavigasi ke halaman ujian dengan leluasa. Cookie dan sesi tetap tersimpan di folder `browser_profile/`.
5. **Ekspor Otomatis**:
   - Seluruh soal, opsi, kunci jawaban, dan pembahasan langsung dirangkum dalam file `hasil_kuis.md` (siap dibaca atau dicetak) dan `hasil_kuis.json`.
6. **Mode Simulasi & Demo Bawaan**:
   - Dilengkapi mock kuis interaktif untuk menguji alur kerja browser langsung di komputer tanpa memerlukan website target aktif atau kuota API.

---

## 🚀 Panduan Memulai Cepat

### 1. Prasyarat
- Python 3.10+ (Sudah terpasang di sistem Anda).
- Google Gemini API Key (Bisa didapatkan gratis di [Google AI Studio](https://aistudio.google.com/)).

### 2. Konfigurasi API Key
Buka file `.env` di folder proyek, lalu masukkan kunci API Anda:
```env
GEMINI_API_KEY=AIzaSy...
```
*(Catatan: Jika belum diisi, program akan menawarkan Anda untuk memasukkannya langsung dari konsol saat dijalankan).*

### 3. Menjalankan Program
Cukup klik ganda file **`run.bat`**, atau jalankan perintah berikut di PowerShell / Terminal:
```powershell
python main.py
```

---

## 🖥️ Menu Program

Saat dijalankan, program menampilkan menu interaktif:

```text
Menu Utama:
  [1] Mulai Kuis Browser (Website Kuis Target Asli)
  [2] Jalankan Simulasi Demo (Uji Coba Otomatis di Layar)
  [3] Mode Tempel Teks / HTML Manual (1 Soal Cepat)
  [4] Keluar
```

### Penjelasan Menu:
- **Pilihan [1] (Kuis Browser Asli)**:
  1. Masukkan URL kuis (atau biarkan kosong jika ingin membuka browser manual).
  2. Browser Chromium akan terbuka. Silakan login atau navigasikan ke halaman kuis Anda.
  3. Saat Anda sudah berada di halaman Soal #1, tekan `[ENTER]` di terminal untuk memulai ekstraksi.
  4. Program akan membaca soal, menampilkan kunci jawaban di terminal, lalu mengklik tombol Next saat Anda menekan `[ENTER]`.
- **Pilihan [2] (Simulasi Demo)**:
  - Membuka halaman kuis simulasi bawaan di browser untuk memperagakan alur deteksi soal -> klik berikutnya -> hingga selesai.
- **Pilihan [3] (Tempel Teks/HTML)**:
  - Untuk memecahkan satu soal dengan cepat cukup dengan copy-paste teks atau HTML ke konsol.

---

## 📁 Struktur Direktori

```text
tak/
├── main.py                # Titik masuk utama program (CLI Interaktif Rich)
├── run.bat                # Shortcut 1-klik untuk Windows
├── requirements.txt       # Daftar dependensi Python
├── .env.example           # Template konfigurasi environment
├── .env                   # Tempat menyimpan GEMINI_API_KEY Anda
├── README.md              # Petunjuk dokumentasi
├── src/
│   ├── models.py          # Definisi skema data Pydantic (Soal, Opsi, Jawaban)
│   ├── gemini_solver.py   # Logika AI ekstraktor & penjawab Gemini 3.8 Flash
│   ├── browser_agent.py   # Pengendali otomasi browser Playwright
│   └── exporter.py        # Modul ekspor ke Markdown dan JSON
└── tests/
    ├── mock_quiz.html     # Halaman simulasi kuis bertahap
    └── test_flow.py       # Pengujian otomatis Playwright & Exporter
```

---

## 📊 Contoh Hasil Output (`hasil_kuis.md`)

```markdown
# Hasil Rekap Soal & Kunci Jawaban

*Total Soal Terjawab: 15*

---

## Soal No. 1
**Pertanyaan:**
Organel sel manakah yang berfungsi sebagai tempat terjadinya proses fotosintesis?

**Pilihan Jawaban:**
- A. Mitokondria
✅ **[KUNCI JAWABAN]** B. Kloroplas
- C. Ribosom
- D. Badan Golgi

> **Kunci Jawaban:** B Kloroplas
>
> **Pembahasan:**
> Kloroplas mengandung pigmen klorofil yang menyerap energi radiasi matahari untuk melangsungkan reaksi fotosintesis pada tumbuhan.
>
> **Keyakinan AI:** 98%
---
```

