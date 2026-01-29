from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware # 👈 [중요] 이거 추가됨!
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
import crawler
import re  # 정규표현식

# DB 테이블 생성
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# =========================================================
# 👇 [필수] 브라우저 접속 허용 설정 (CORS)
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 곳에서 접속 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# =========================================================

# DB 세션
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. 크롤링 실행 (POST)
@app.post("/api/crawl/run")
def run_crawl(db: Session = Depends(get_db)):
    print(">> 크롤링 요청 받음! 시작합니다...")
    
    # 1. 크롤러 실행
    try:
        data_list = crawler.scrape_musinsa()
    except Exception as e:
        return {"status": "fail", "message": f"에러: {str(e)}"}

    # 2. 데이터가 비어있으면 중단
    if not data_list:
        return {"status": "fail", "message": "가져온 데이터가 없습니다."}

    # 3. 기존 데이터 비우기 (초기화)
    db.query(models.MusinsaItem).delete()
    db.commit()

    # 내부 함수: 숫자만 깔끔하게 남기는 청소부
    def clean_number(value):
        if not value: return 0 
        # 숫자(0-9)가 아닌 건 전부 지워버림
        numbers = re.sub(r'[^0-9]', '', str(value))
        return int(numbers) if numbers else 0

    count = 0
    # 4. 데이터 저장
    for item in data_list:
        db_item = models.MusinsaItem(
            ranking=clean_number(item.get('ranking')),      
            brand=item.get('brand'),
            title=item.get('title'),
            price=clean_number(item.get('price')),          
            img_url=item.get('img_url'),
            category=item.get('category'),
            like_count=clean_number(item.get('like_count')), 
            rating=clean_number(item.get('rating')),        
            review_count=clean_number(item.get('review_count')), 
            sub_img=item.get('sub_img'),
            view_count=clean_number(item.get('view_count'))  
        )
        db.add(db_item)
        count += 1
    
    db.commit()
    return {"status": "success", "saved_count": count}

# 2. 데이터 조회 (GET)
@app.get("/api/items")
def get_items(category: str = None, db: Session = Depends(get_db)):
    """
    모든 상품을 JSON으로 보여줍니다.
    ?category=상의 처럼 검색할 수도 있습니다.
    """
    if category:
        items = db.query(models.MusinsaItem).filter(models.MusinsaItem.category == category).all()
    else:
        items = db.query(models.MusinsaItem).all()
    
    return items