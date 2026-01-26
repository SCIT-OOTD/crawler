from sqlalchemy import Column, Integer, String, Float, Text
from database import Base

class MusinsaItem(Base):
    __tablename__ = "musinsa_item"  # MySQL에 저장될 테이블 이름

    id = Column(Integer, primary_key=True, index=True)
    sub_img = Column(Text, nullable=True) #
    ranking = Column(Integer)
    brand = Column(String(255))
    title = Column(String(255))
    price = Column(Integer)
    img_url = Column(Text)
    category = Column(String(50))
    like_count = Column(Integer)    # 좋아요 (숫자)
    rating = Column(Float)          # 평점 (실수)
    review_count = Column(Integer)  # 후기 수