# SmartKaraokeAI

Ứng dụng Android hỗ trợ phân tích bản thu giọng hát và gợi ý thông số EQ,
Echo, Reverb. Người dùng điều chỉnh thiết bị bằng tay theo hướng dẫn;
ứng dụng chưa tự điều khiển phần cứng.

## Thành phần

- `mobile-app/`: Kotlin, Jetpack Compose, quản lý trạng thái bằng ViewModel.
- `backend-ai/`: Python, FastAPI, Librosa, SQLite; bộ luật và mô hình JBL tùy chọn.
- Thiết bị mục tiêu: JBL K12 Plus và Beta Three FX99 Plus.

## Chạy backend trên Windows

Cài Python 3.11 kèm Python Launcher; cần mạng để cài thư viện lần đầu.
Mở PowerShell tại thư mục dự án:

```powershell
cd backend-ai
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

Backend chạy trên cổng 8000. Kiểm tra tại `http://127.0.0.1:8000/health`,
tài liệu API tại `http://127.0.0.1:8000/docs`.

Để xử lý MP4/M4A, cài thêm FFmpeg/FFprobe trước khi khởi động backend:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-media.ps1
```

WAV/FLAC/OGG không cần bước cài FFmpeg.

## Chạy ứng dụng Android

1. Mở `mobile-app/` trong Android Studio và chờ Gradle Sync hoàn tất.
2. Cấu hình Android SDK trên máy hiện tại rồi chạy trên điện thoại/emulator.
3. Điện thoại cần Android 7.0 trở lên; kết nối cùng mạng với máy tính.
4. Nhập `http://<IPv4-máy-tính>:8000` trong cài đặt kết nối của ứng dụng.
   Emulator có thể dùng `http://10.0.2.2:8000`.
5. Chọn bản thu giọng hát riêng, dài 1–60 giây, tối đa 20 MiB và bấm phân tích.

APK cần backend để phân tích. `127.0.0.1` trên điện thoại chỉ dùng để kết nối
backend máy tính khi đã thiết lập ADB reverse qua USB.

Xuất APK debug từ PowerShell tại `mobile-app/`:

```powershell
.\gradlew.bat assembleDebug
```

File được tạo tại `app/build/outputs/apk/debug/app-debug.apk`.

## Mô hình thử nghiệm

Backend mặc định dùng bộ luật. Dữ liệu mô hình JBL là **48 mẫu mô phỏng**,
không phải dữ liệu bản thu thực có nhãn được chuyên gia xác nhận.
Mô hình dùng 15 đầu vào (13 MFCC trung bình, cao độ, RT60) và dự đoán
7 thông số; Reverb mode cố định bằng 2. Hiệu quả chỉnh âm và ánh xạ
điều khiển thiết bị thực chưa được xác minh.

Dữ liệu JSONL và mô hình joblib không được đưa vào Git; tạo lại từ mã nguồn
bằng các lệnh sau tại `backend-ai/`, sau khi cài môi trường:

```powershell
.\.venv\Scripts\python.exe data\generate_realistic_dataset.py
.\.venv\Scripts\python.exe train_model.py data\expert_labels_v2.jsonl --output models\demo --allow-mock
$env:SMARTKARAOKE_JBL_MODEL = (Resolve-Path .\models\demo\jbl_k12_plus_v2.joblib).Path
$env:SMARTKARAOKE_ENABLE_MOCK_MODEL = '1'
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

Đầu vào thiếu điều kiện, ngoài miền huấn luyện hoặc mô hình không tương thích
sẽ quay về bộ luật. RT60 và kiểu giọng do người dùng cung cấp; hệ thống
chưa tự đo RT60 hoặc tự phân loại kiểu giọng.

## Kiểm thử

Tại `backend-ai/`, sau khi chạy setup:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Android có kiểm thử thang núm tại `DialScaleTest.kt`.

Môi trường Python, bộ nhớ đệm, lịch sử SQLite, APK và khóa ký không được
đưa vào repository. Có thể phát hành APK riêng qua GitHub Releases.
