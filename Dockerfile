# 1. 베이스 이미지
FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

ENV PYTHONUNBUFFERED=1
# 2. 작업 폴더 설정 (/app)
WORKDIR /app

# 3. 라이브러리 설치
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 4. 소스 코드 전체 복사 (python 폴더도 같이 들어옴)
COPY . .



# 5. [중요] 작업 폴더를 'python' 폴더 안으로 변경! 📂
WORKDIR /app/python

# 6. 이제 crawler.py가 바로 옆에 있으니 실행

CMD ["uvicorn", "fastapi_server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]