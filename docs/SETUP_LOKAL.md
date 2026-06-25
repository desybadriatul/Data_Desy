# Setup Lokal — Tahap 1: Buktikan Connector Hidup

Ikuti urutan ini. Jangan loncat langkah.

## 1. Pastikan Python terinstall

Buka Terminal (Mac) atau Command Prompt/PowerShell (Windows), ketik:
```
python3 --version
```
Kalau muncul versi (misal `Python 3.11.x`), lanjut ke langkah 2.
Kalau error/tidak ada, install Python dulu dari https://www.python.org/downloads/
(saat install di Windows, centang "Add Python to PATH").

## 2. Buka folder project di Terminal

Di VS Code, buka folder `sonar-mcp` (File > Open Folder). Lalu buka Terminal
di dalam VS Code (menu Terminal > New Terminal). Terminal ini otomatis
sudah berada di folder `sonar-mcp`.

## 3. Buat virtual environment (supaya rapi, tidak bercampur project lain)

```
python3 -m venv venv
```

Aktifkan:
- Mac/Linux: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

Kalau berhasil, di awal baris Terminal akan muncul tulisan `(venv)`.

## 4. Install library yang dibutuhkan

```
pip install -r requirements.txt
```

Tunggu sampai selesai (tidak ada tulisan error merah di akhir).

## 5. Cek server.py bisa jalan (tanpa Claude dulu)

```
python server.py
```

Kalau tidak ada error dan terminal "menggantung" (seperti menunggu), itu
artinya server BERHASIL jalan dan sedang menunggu koneksi. Tekan
`Ctrl+C` untuk menghentikannya — ini baru tes bahwa kodenya tidak error.

## 6. Sambungkan ke Claude Desktop

Cari file konfigurasi Claude Desktop:
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Kalau file belum ada, buat file baru dengan nama itu. Isi (atau tambahkan)
seperti ini — **ganti `/PATH/KE/sonar-mcp` dengan lokasi folder project
kamu yang sebenarnya**:

```json
{
  "mcpServers": {
    "cogan": {
      "command": "/PATH/KE/sonar-mcp/venv/bin/python3",
      "args": ["/PATH/KE/sonar-mcp/server.py"]
    }
  }
}
```

Kalau di Windows, `command` biasanya:
`"C:\\PATH\\KE\\sonar-mcp\\venv\\Scripts\\python.exe"`

Cara dapat path lengkap folder kamu: di Terminal (masih di folder
sonar-mcp), ketik `pwd` (Mac) atau `cd` (Windows) — hasilnya itu yang
dipakai untuk ganti `/PATH/KE/sonar-mcp`.

## 7. Restart Claude Desktop

Tutup Claude Desktop sepenuhnya, buka lagi.

## 8. Tes di Claude Desktop

Ketik ke Claude:
```
Cek koneksi Cogan
```

Kalau Claude menjawab dengan hasil yang mengandung kalimat
"Cogan is connected." — **berhasil**. Lanjut ke tahap 2 (find_project).

Kalau gagal: buka log error di
`~/Library/Logs/Claude/mcp-server-cogan.log` (Mac) atau
`%APPDATA%\Claude\logs\` (Windows), lalu cek pesan errornya — biasanya
soal path yang salah ketik.
