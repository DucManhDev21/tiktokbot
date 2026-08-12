# Sử dụng Image chuẩn chứa sẵn Python và Playwright/Chromium từ Microsoft
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Thiết lập thư mục làm việc trong Container
WORKDIR /app

# Biến môi trường giúp Python chạy mượt, không ghi file buffer rác
ENV PYTHONUNBUFFERED=1

# Copy toàn bộ file trong dự án vào Container
COPY . /app

# Cài đặt các thư viện Python cần thiết
RUN pip install --no-cache-dir google-genai schedule playwright

# Lệnh chạy ứng dụng tự động khi khởi động Container
CMD ["python", "tool.py"]

