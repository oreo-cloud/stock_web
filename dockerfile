# 1. 選擇作業系統＋Python 基底映像
FROM python:3.11-slim

# 2. 設定工作目錄
WORKDIR /app

# 3. 複製並安裝相依套件
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 4. 複製專案程式
COPY . .

# 5. 暴露 Flask 預設的 5000 port
EXPOSE 5000

# 6. 啟動指令
#    開發用：使用 flask run
#    如果要用 Gunicorn，可改成：CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
CMD ["flask", "run", "--host=0.0.0.0"]
