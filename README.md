# Gesture LED Controller

Kontrol tiga kanal LED RGB dengan gerakan tangan melalui webcam. Program Python mendeteksi tangan, menampilkan antarmuka kontrol, lalu mengirim nilai kecerahan ke Arduino melalui Serial.

## Isi repositori

- `gesture_control.py` — program webcam, deteksi tangan, dan antarmuka kontrol.
- `hand_landmarker.task` — model MediaPipe untuk deteksi tangan. Simpan di folder yang sama dengan `gesture_control.py`.
- `requirements.txt` — daftar pustaka Python yang diperlukan.
- `led_gesture_controller/led_gesture_controller.ino` — sketch yang diunggah ke Arduino.

## Perangkat keras

Contoh ini menggunakan Arduino Uno dan tiga kanal LED dengan koneksi:

| Warna | Pin Arduino |
|---|---:|
| Merah | 9 |
| Hijau | 10 |
| Biru | 11 |

Ketiga pin tersebut mendukung PWM pada Arduino Uno. Gunakan resistor pembatas arus yang sesuai untuk setiap LED/kanal RGB, dan sambungkan GND rangkaian LED ke GND Arduino. Sketch ini menganggap LED common-cathode; LED common-anode memerlukan pembalikan nilai PWM pada sketch.

## Persiapan Arduino

1. Buka `led_gesture_controller/led_gesture_controller.ino` di Arduino IDE.
2. Pilih board dan port Arduino yang benar.
3. Unggah sketch ke board.
4. Tutup Serial Monitor sebelum menjalankan program Python agar port serial tidak sedang digunakan aplikasi lain.

## Persiapan Python di Windows

Gunakan Python 3.14. Buka PowerShell pada folder proyek, lalu jalankan:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Jalankan program:

```powershell
.\.venv\Scripts\python.exe gesture_control.py
```

Pastikan webcam terhubung dan file `hand_landmarker.task` berada di folder proyek.

## Pengaturan port serial

Secara default, program menggunakan `COM6` dengan baud rate `115200`. Jika Arduino muncul pada port lain di komputer Anda, ubah nilai `SERIAL_PORT` di bagian atas `gesture_control.py`, misalnya:

```python
SERIAL_PORT = 'COM3'
```

Baud rate Python dan sketch Arduino harus sama (`115200`).

## Cara menggunakan

- Arahkan telunjuk ke tombol lampu, lalu satukan ibu jari dan telunjuk (pinch) untuk mengubah status lampu.
- Untuk mengatur kecerahan, tahan pinch sambil menggerakkan telunjuk di sepanjang slider lampu.
- Tekan `1`, `2`, atau `3` untuk menyalakan/mematikan lampu merah, hijau, atau biru.
- Tekan `0` untuk mematikan semua lampu.
- Tekan `Q` atau `Esc` untuk keluar.

Program memproses video webcam secara langsung dan tidak menyimpan rekaman video.

## Pemecahan masalah

- **Model tidak ditemukan:** pastikan `hand_landmarker.task` berada satu folder dengan `gesture_control.py`.
- **Arduino gagal terhubung:** periksa `SERIAL_PORT`, kabel USB, dan pastikan Serial Monitor/IDE tidak sedang memakai port tersebut.
- **Kamera tidak terbuka:** tutup aplikasi lain yang menggunakan webcam dan periksa sambungan kamera.
- **Warna lampu tertukar:** cocokkan kabel merah, hijau, dan biru dengan pin 9, 10, dan 11 pada tabel di atas.
