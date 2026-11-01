FROM python:3.10-slim

# Tesseract OCR ইনস্টল করা হচ্ছে
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# পোর্ট এক্সপোজ করা (ফ্রি হোস্টিংয়ের জন্য)
EXPOSE 8080

CMD ["python", "main.py"]