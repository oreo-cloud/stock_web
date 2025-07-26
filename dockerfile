FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 這裡安裝 curl 與 ping (ping 在套件 iputils-ping 中)
RUN apt-get update \
    && apt-get install -y curl iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]
