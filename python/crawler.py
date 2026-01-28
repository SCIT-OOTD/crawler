from playwright.sync_api import sync_playwright
import sys
import time
import re
import pymysql

# 1. DB 설정 (도커 컨테이너 이름 확인 필수!)
db_config = {
    'host': 'ootd-db',   # docker-compose의 서비스 이름
    'user': 'root',
    'password': '1234',  # docker-compose의 MYSQL_ROOT_PASSWORD와 일치해야 함
    'database': 'musinsa_db',
    'port': 3306,
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def parse_korean_number(text):
    if not text: return 0
    text = str(text).strip()
    multiplier = 1
    if '만' in text:
        multiplier = 10000
        text = text.replace('만', '')
    elif '천' in text:
        multiplier = 1000
        text = text.replace('천', '')
    clean_num = re.sub(r"[^0-9.]", "", text)
    if clean_num:
        try:
            return int(float(clean_num) * multiplier)
        except:
            return 0
    return 0

def scrape_musinsa():
    total_results = []
    # 카테고리별 URL 정의
    CATEGORY_URLS = {
        "상의": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=001000",
        "하의": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=003000",
        "신발": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=005000",
        "아우터": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=002000"
    }

    print(">> [무신사] 통합 크롤링 시작...", flush=True)

    # [중요] with 구문 안에서 모든 브라우저 작업이 이루어져야 함
    with sync_playwright() as p:
        # ⚠️ Docker에서는 반드시 headless=True 여야 합니다!
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_name, cat_url in CATEGORY_URLS.items():
            print(f"\n>> 🚀 [{cat_name}] 수집 시작...", flush=True)
            try:
                page.goto(cat_url, timeout=60000)
                time.sleep(2)

                # 스크롤 내리기 (데이터 로딩)
                for _ in range(3): 
                    page.keyboard.press("PageDown")
                    time.sleep(1)
                
                # 상품 링크 가져오기
                items_data = page.evaluate("""() => {
                    const data = [];
                    const links = Array.from(document.querySelectorAll("a"));
                    const productLinks = links.filter(a => 
                        (a.href.includes('/goods/') || a.href.includes('/products/')) && 
                        !a.href.includes('reviews')
                    );
                    // 테스트를 위해 5개만 수집
                    productLinks.slice(0, 5).forEach(a => { data.push({ href: a.href }); });
                    return data;
                }""")

                # 중복 제거
                target_items = []
                seen = set()
                for item in items_data:
                    url = item['href'].split('?')[0]
                    if url not in seen:
                        seen.add(url)
                        target_items.append(item)

                # 상세 페이지 이동 및 데이터 추출
                for idx, item in enumerate(target_items):
                    try:
                        page.goto(item['href'], timeout=60000)
                        time.sleep(1) 

                        extracted = page.evaluate("""() => {
                            const getMeta = (p) => document.querySelector(`meta[property="${p}"]`)?.content || "";
                            return {
                                title: getMeta('og:title'),
                                brand: getMeta('product:brand'),
                                img: getMeta('og:image'),
                                price: getMeta('product:price:amount')
                            };
                        }""")

                        price_int = int(extracted['price']) if extracted['price'] else 0
                        
                        data = {
                            "ranking": idx + 1,
                            "brand": extracted['brand'] if extracted['brand'] else "무신사",
                            "title": extracted['title'],
                            "price": price_int,
                            "img_url": extracted['img'],
                            "category": cat_name,
                            "link": item['href'],
                            "like_count": 0,
                            "rating": 0.0,
                            "review_count": 0,
                            "view_count": 0
                        }
                        total_results.append(data)
                        print(f"  - 수집성공: {data['title'][:15]}...")

                    except Exception as e:
                        print(f"  - 개별 상품 에러: {e}")
            
            except Exception as e:
                print(f"[{cat_name}] 카테고리 에러: {e}")

        browser.close()
    
    return total_results

# [수정됨] DB 연결이 될 때까지 기다리는 안전한 초기화 함수
def init_db():
    retries = 30  # 30번 시도 (약 90초 대기)
    while retries > 0:
        try:
            print(f">> DB 접속 시도 중... (남은 시도: {retries})")
            conn = pymysql.connect(**db_config)
            cursor = conn.cursor()
            
            # 테이블 생성 쿼리
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS musinsa_item (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255),
                brand VARCHAR(100),
                price INT,
                img_url TEXT,
                category VARCHAR(50),
                link TEXT,
                ranking INT,
                like_count INT DEFAULT 0,
                rating FLOAT DEFAULT 0.0,
                review_count INT DEFAULT 0,
                view_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_table_sql)
            conn.commit()
            print(">> ✅ DB 연결 및 테이블 확인 완료! (성공)")
            conn.close()
            return  # 성공하면 함수 종료
            
        except pymysql.err.OperationalError as e:
            # DB가 켜지는 중이라 접속이 거부되면 여기서 걸립니다.
            print(f"   ⏳ DB 부팅 대기 중... 3초 뒤 재시도. (에러코드: {e.args[0]})")
            time.sleep(3)
            retries -= 1
            
        except Exception as e:
            print(f"❌ 예상치 못한 에러: {e}")
            time.sleep(3)
            retries -= 1
            
    print("❌❌ DB 접속 최종 실패. 도커 로그를 확인해주세요.")
    sys.exit(1) # 강제 종료

def save_to_db(items):
    if not items:
        print("저장할 데이터가 없습니다.")
        return

    print(f"\n>> DB 저장 시작 ({len(items)}개)...")
    
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()

        sql = """
            INSERT INTO musinsa_item 
            (title, brand, price, img_url, category, link, ranking, like_count, rating, review_count, view_count) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for item in items:
            cursor.execute(sql, (
                item['title'], 
                item['brand'], 
                item['price'], 
                item['img_url'], 
                item['category'],
                item.get('link', '#'),
                item['ranking'],
                item['like_count'],
                item['rating'],
                item['review_count'],
                item['view_count']
            ))
        
        conn.commit()
        print(">> ✅ DB 저장 진짜 완료!")
        
    except Exception as e:
        print(f"❌ DB 저장 중 에러 발생: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # 1. DB 준비 (연결될 때까지 대기 후 테이블 생성)
    init_db()

    # 2. 크롤링 실행
    crawled_data = scrape_musinsa()
    
    # 3. DB 저장 실행
    save_to_db(crawled_data)