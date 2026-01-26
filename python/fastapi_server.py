from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
import crawler 

# DB 테이블 생성
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# DB 세션
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. [기존] 크롤링 실행 (POST)
@app.post("/api/crawl/run")
def run_crawl(db: Session = Depends(get_db)):
    print(">> 크롤링 요청 받음! 시작합니다...")
    try:
        data_list = crawler.scrape_musinsa()
    except Exception as e:
        return {"status": "fail", "message": f"에러: {str(e)}"}

    # 기존 데이터 비우기 (선택사항)
    db.query(models.MusinsaItem).delete()
    db.commit()

    count = 0
    for item in data_list:
        db_item = models.MusinsaItem(
            ranking=item['ranking'],
            brand=item['brand'],
            title=item['title'],
            price=item['price'],
            img_url=item['img_url'],
            category=item['category'],
            like_count=item['like_count'],
            rating=item['rating'],
            review_count=item['review_count'],
            sub_img=item['sub_img'],
            view_count=item['view_count']
        )
        db.add(db_item)
        count += 1
    
    db.commit()
    return {"status": "success", "saved_count": count}

# 🆕 2. [추가] 데이터 조회 (GET) - 브라우저에서 보는 용도!
@app.get("/api/items")
def get_items(category: str = None, db: Session = Depends(get_db)):
    """
    모든 상품을 JSON으로 보여줍니다.
    ?category=상의 처럼 검색할 수도 있습니다.
    """
    if category:
        # 카테고리가 있으면(예: 상의) 그것만 필터링해서 가져옴
        items = db.query(models.MusinsaItem).filter(models.MusinsaItem.category == category).all()
    else:
        # 없으면 전체 다 가져옴
        items = db.query(models.MusinsaItem).all()
    
    return items