from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. DB 연결 주소 (비밀번호 확인 필수!)
# 사용자명: root, 비밀번호: 1234 (본인 비밀번호로 변경), DB명: musinsa_db
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@db:3306/musinsa_db"

# 2. 엔진 생성 (DB와 연결하는 기계)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)

# 3. 세션 공장 만들기 (데이터를 주고받을 통로)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 베이스 모델 (모든 테이블의 조상)
Base = declarative_base()