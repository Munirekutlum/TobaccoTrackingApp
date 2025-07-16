# 1. Python 3.10 slim imajı baz alınıyor
FROM python:3.10-slim

# 2. Sistem bağımlılıklarını kur
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    apt-transport-https \
    unixodbc-dev

# 3. Microsoft ODBC Driver deposunu ekle ve sürücüyü kur
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg \
    && echo "deb [arch=amd64] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18

# 4. Çalışma dizinini ayarla
WORKDIR /app

# 5. Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Proje dosyalarını kopyala
COPY . .

# 7. Uygulamayı gunicorn ile başlat, port ortam değişkeninden alınacak
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
