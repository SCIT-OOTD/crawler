from sqlalchemy import Column, Integer, String, Float, Text
from database import Base

class MusinsaItem(Base):
    __tablename__ = "musinsa_item"

    id = Column(Integer, primary_key=True, index=True)
    ranking = Column(Integer)
    brand = Column(String(100))
    title = Column(String(255))
    price = Column(Integer)
    img_url = Column(String(500))
    category = Column(String(50))
    
    # 상세 정보
    like_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    
    # 긴 이미지 주소 저장용
    sub_img = Column(Text, nullable=True) 
    
    # 🔴 [추가됨] 조회수 저장용 칸
    view_count = Column(Integer, default=0)