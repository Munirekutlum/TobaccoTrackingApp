# 1. Python 3.10 slim imajı baz alınıyor
FROM python:3.10-slim

# 2. Sistem bağımlılıklarını kur
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Microsoft ODBC Driver deposunu ekle ve sürücüyü kur
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# 4. Çalışma dizinini ayarla
WORKDIR /app

# 5. Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Proje dosyalarını kopyala
COPY . .

# 7. Uygulamayı gunicorn ile başlat, port ortam değişkeninden alınacak
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "app:app"]
