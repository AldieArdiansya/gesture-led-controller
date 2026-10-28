import math
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import serial
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ----------------- KONFIGURASI SERIAL ----------------- #
SERIAL_PORT = 'COM6'
BAUD_RATE = 115200

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2)
    print(f"[INFO] Berhasil terhubung ke Arduino pada {SERIAL_PORT}")
except Exception as e:
    print(f"[PERINGATAN] Gagal membuka port {SERIAL_PORT}: {e}")
    print("[INFO] Program berjalan dalam mode simulasi.")
    arduino = None

# ------------- INISIALISASI MEDIAPIPE HANDS ----------- #
MODEL_PATH = Path(__file__).resolve().with_name("hand_landmarker.task")
if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"Model MediaPipe tidak ditemukan: {MODEL_PATH}. "
        "Pastikan file hand_landmarker.task berada di folder yang sama."
    )

base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
hand_landmarker_options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7,
)
hands = vision.HandLandmarker.create_from_options(hand_landmarker_options)

# Inisialisasi Webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ----------------- STRUKTUR KONTROL UI ----------------- #
# Posisi elemen antarmuka pada frame 640x480.
SLIDER_X_START = 215
SLIDER_X_END = 520

# Data 3 Lampu (Merah, Hijau, Biru)
leds = [
    {
        "name": "MERAH",
        "color": (0, 0, 255),      # BGR: Merah
        "btn_rect": (42, 105, 166, 151),
        "slider_y": 128,
        "is_on": False,
        "brightness": 200,          # Nilai kecerahan saat aktif (0-255)
        "btn_clicked_prev": False   # Untuk debounce klik
    },
    {
        "name": "HIJAU",
        "color": (0, 255, 0),      # BGR: Hijau
        "btn_rect": (42, 202, 166, 248),
        "slider_y": 225,
        "is_on": False,
        "brightness": 200,
        "btn_clicked_prev": False
    },
    {
        "name": "BIRU",
        "color": (255, 100, 0),    # BGR: Biru
        "btn_rect": (42, 299, 166, 345),
        "slider_y": 322,
        "is_on": False,
        "brightness": 200,
        "btn_clicked_prev": False
    }
]

last_sent_values = (-1, -1, -1)
active_slider_idx = None  # Menyimpan slider mana yang sedang digeser

print("[INFO] Program GUI Virtual Berjalan.")
print("[PETUNJUK] Arahkan telunjuk lalu pinch untuk menekan tombol atau menggeser slider.")
print("[PETUNJUK] Pintasan: 1/2/3 toggle lampu, 0 semua mati, Q keluar.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Cermin frame secara horizontal
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    # Deteksi Tangan dengan MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int(time.monotonic() * 1000)
    results = hands.detect_for_video(mp_image, timestamp_ms)

    # Koordinat jari
    cursor_x, cursor_y = -1, -1
    is_pinching = False

    if results.hand_landmarks:
        for hand_landmarks in results.hand_landmarks:
            landmark_points = [
                (int(landmark.x * w), int(landmark.y * h))
                for landmark in hand_landmarks
            ]

            # Garis rangka tangan dengan outline gelap agar tetap jelas di video.
            for connection in vision.HandLandmarksConnections.HAND_CONNECTIONS:
                start = landmark_points[connection.start]
                end = landmark_points[connection.end]
                cv2.line(frame, start, end, (20, 35, 40), 6, cv2.LINE_AA)
                cv2.line(frame, start, end, (0, 220, 190), 2, cv2.LINE_AA)

            # Titik sendi dan ujung jari.
            for landmark_id, point in enumerate(landmark_points):
                is_fingertip = landmark_id in (4, 8, 12, 16, 20)
                joint_color = (0, 230, 255) if is_fingertip else (235, 248, 255)
                cv2.circle(frame, point, 7 if is_fingertip else 5, (20, 35, 40), cv2.FILLED, cv2.LINE_AA)
                cv2.circle(frame, point, 4 if is_fingertip else 2, joint_color, cv2.FILLED, cv2.LINE_AA)

            # Koordinat Ibu Jari (4) dan Telunjuk (8)
            thumb = hand_landmarks[4]
            index = hand_landmarks[8]

            tx, ty = int(thumb.x * w), int(thumb.y * h)
            ix, iy = int(index.x * w), int(index.y * h)

            cursor_x, cursor_y = ix, iy

            # Hitung jarak cubitan (pinch) antara ibu jari & telunjuk
            pinch_dist = math.hypot(ix - tx, iy - ty)
            is_pinching = pinch_dist < 40  # Kurang dari 40 piksel = mode KLIK / GESER

            # Gambar visual kursor di ujung telunjuk
            cursor_color = (0, 255, 255) if is_pinching else (255, 255, 255)
            cv2.circle(frame, (cursor_x, cursor_y), 10, cursor_color, cv2.FILLED)
            cv2.circle(frame, (cursor_x, cursor_y), 12, (0, 0, 0), 2)

            if is_pinching:
                # Garis penghubung pinch
                cv2.line(frame, (tx, ty), (ix, iy), (0, 255, 255), 2)

    # ------------------ LOGIKA INTERAKSI UI ------------------ #
    if cursor_x != -1 and cursor_y != -1:
        for idx, led in enumerate(leds):
            x1, y1, x2, y2 = led["btn_rect"]

            # 1. CEK INTERAKSI TOMBOL ON / OFF
            if x1 <= cursor_x <= x2 and y1 <= cursor_y <= y2:
                if is_pinching:
                    if not led["btn_clicked_prev"]:
                        led["is_on"] = not led["is_on"]  # Toggle status ON/OFF
                        led["btn_clicked_prev"] = True
                else:
                    led["btn_clicked_prev"] = False
            else:
                if not is_pinching:
                    led["btn_clicked_prev"] = False

            # 2. CEK INTERAKSI SLIDER (GESER KE KANAN / KIRI)
            sy = led["slider_y"]
            # Toleransi area sentuh slider (+- 20px vertikal)
            if is_pinching:
                if (active_slider_idx is None or active_slider_idx == idx):
                    if (SLIDER_X_START - 20 <= cursor_x <= SLIDER_X_END + 20) and (sy - 20 <= cursor_y <= sy + 20):
                        active_slider_idx = idx
                        # Konversi posisi X kursor menjadi nilai PWM 0 - 255
                        clamped_x = np.clip(cursor_x, SLIDER_X_START, SLIDER_X_END)
                        new_brightness = int(np.interp(clamped_x, [SLIDER_X_START, SLIDER_X_END], [0, 255]))
                        led["brightness"] = new_brightness
                        
                        # Jika digeser di atas 0, otomatis aktifkan lampu
                        if new_brightness > 0:
                            led["is_on"] = True
                        else:
                            led["is_on"] = False
    else:
        active_slider_idx = None

    if not is_pinching:
        active_slider_idx = None

    # ------------------ MENGGAMBAR ANTARMUKA (GUI) ------------------ #
    # Header dan status koneksi tanpa panel latar agar video tetap terlihat.
    cv2.putText(frame, "GESTURE LED STUDIO", (36, 43), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (245, 248, 255), 2)
    cv2.putText(frame, "KONTROL LAMPU BERBASIS GESTUR", (37, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (165, 180, 198), 1)

    connection_color = (75, 220, 130) if arduino is not None else (0, 190, 255)
    connection_label = "ARDUINO TERHUBUNG" if arduino is not None else "MODE SIMULASI"
    cv2.circle(frame, (430, 42), 5, connection_color, cv2.FILLED)
    cv2.putText(frame, connection_label, (443, 47), cv2.FONT_HERSHEY_SIMPLEX, 0.43, connection_color, 1)

    # Kartu lampu dan kontrol slider.
    for idx, led in enumerate(leds):
        card_y = 88 + idx * 97
        x1, y1, x2, y2 = led["btn_rect"]
        sy = led["slider_y"]
        led_color = led["color"]
        is_hovered = cursor_x != -1 and 24 <= cursor_x <= 616 and card_y <= cursor_y <= card_y + 84

        # Tombol tanpa bidang isi; hanya bingkai dan teks yang menimpa video.
        border_color = led_color if led["is_on"] else (205, 215, 228)
        cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, 2 if is_hovered or led["is_on"] else 1)
        cv2.putText(frame, led["name"], (x1 + 10, y1 + 19), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (240, 244, 250), 1)
        btn_text = "NYALA" if led["is_on"] else "MATI"
        cv2.putText(frame, btn_text, (x1 + 10, y1 + 38), cv2.FONT_HERSHEY_SIMPLEX, 0.53, (255, 255, 255), 2)

        # Slider dengan area interaksi lebar dan nilai kecerahan.
        cv2.putText(frame, "KECERAHAN", (SLIDER_X_START, sy - 19), cv2.FONT_HERSHEY_SIMPLEX, 0.37, (165, 180, 198), 1)
        cv2.line(frame, (SLIDER_X_START, sy), (SLIDER_X_END, sy), (75, 87, 105), 8)
        handle_x = int(np.interp(led["brightness"], [0, 255], [SLIDER_X_START, SLIDER_X_END]))
        if led["is_on"]:
            cv2.line(frame, (SLIDER_X_START, sy), (handle_x, sy), led_color, 8)
        cv2.circle(frame, (handle_x, sy), 13, (18, 24, 34), cv2.FILLED)
        cv2.circle(frame, (handle_x, sy), 9, led_color if led["is_on"] else (125, 139, 158), cv2.FILLED)
        cv2.circle(frame, (handle_x, sy), 12, (235, 240, 248), 1)

        display_val = str(led["brightness"]) if led["is_on"] else "OFF"
        cv2.putText(frame, display_val, (536, sy + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (245, 248, 255), 1)

    # Petunjuk gestur dan pintasan keyboard.
    if cursor_x == -1:
        gesture_label = "TANGAN BELUM TERDETEKSI"
        gesture_color = (0, 190, 255)
    elif is_pinching:
        gesture_label = "PINCH AKTIF - TAHAN UNTUK GESER"
        gesture_color = (0, 230, 255)
    else:
        gesture_label = "SIAP - ARAHKAN TELUNJUK, LALU PINCH"
        gesture_color = (90, 225, 150)
    cv2.putText(frame, gesture_label, (40, 403), cv2.FONT_HERSHEY_SIMPLEX, 0.43, gesture_color, 1)
    cv2.putText(frame, "PINCH: tombol ON/OFF atau geser slider", (40, 425), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (220, 228, 238), 1)
    cv2.putText(frame, "PINTASAN: 1/2/3 lampu   |   0 semua mati   |   Q keluar", (40, 449), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (165, 180, 198), 1)

    # Kursor tangan berubah warna saat pinch agar status klik mudah terlihat.
    if cursor_x != -1 and cursor_y != -1:
        cursor_color = (0, 230, 255) if is_pinching else (245, 248, 255)
        cv2.circle(frame, (cursor_x, cursor_y), 15, (18, 24, 34), cv2.FILLED)
        cv2.circle(frame, (cursor_x, cursor_y), 11, cursor_color, 2)
        cv2.circle(frame, (cursor_x, cursor_y), 3, cursor_color, cv2.FILLED)

    # ------------------ PENGIRIMAN DATA KE ARDUINO ------------------ #
    # Hitung nilai aktual yang dikirim (0 jika tombol OFF)
    send_r = leds[0]["brightness"] if leds[0]["is_on"] else 0
    send_g = leds[1]["brightness"] if leds[1]["is_on"] else 0
    send_b = leds[2]["brightness"] if leds[2]["is_on"] else 0

    current_values = (send_r, send_g, send_b)

    if arduino is not None:
        # Kirim jika terjadi perubahan nilai
        if (abs(current_values[0] - last_sent_values[0]) >= 3 or
            abs(current_values[1] - last_sent_values[1]) >= 3 or
            abs(current_values[2] - last_sent_values[2]) >= 3):
            data_to_send = f"{send_r},{send_g},{send_b}\n"
            try:
                arduino.write(data_to_send.encode())
                last_sent_values = current_values
            except Exception as e:
                print(f"[ERROR Serial]: {e}")

    # Tampilkan jendela dan pintasan keyboard.
    cv2.imshow("Virtual LED Controller", frame)
    key = cv2.waitKey(1) & 0xFF
    if key in (ord('q'), 27):
        break
    elif key in (ord('1'), ord('2'), ord('3')):
        led_idx = key - ord('1')
        leds[led_idx]["is_on"] = not leds[led_idx]["is_on"]
    elif key == ord('0'):
        for led in leds:
            led["is_on"] = False

# Pembersihan
cap.release()
cv2.destroyAllWindows()
hands.close()
if arduino is not None:
    arduino.write(b"0,0,0\n")
    arduino.close()

print("[INFO] Program selesai.")