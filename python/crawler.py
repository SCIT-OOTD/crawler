from playwright.sync_api import sync_playwright
import sys
import time
import re
import pymysql

# 1. DB 설정
db_config = {
    'host': 'mysql-container',   # docker-compose 서비스 이름
    'user': 'root',
    'password': '1234',          # docker-compose 비번 일치 확인
    'database': 'musinsa_db',    # DB 이름 일치 확인
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
    CATEGORY_URLS = {
        "상의": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=001000",
        "하의": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=003000",
        "신발": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=005000",
        "아우터": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=002000"
    }

    print(">> [무신사] 통합 크롤링 시작...", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_name, cat_url in CATEGORY_URLS.items():
            print(f"\n>> 🚀 [{cat_name}] 수집 시작...", flush=True)
            try:
                page.goto(cat_url, timeout=60000)
                time.sleep(2)

                # 스크롤
                for _ in range(3): 
                    page.keyboard.press("PageDown")
                    time.sleep(1)
                
                # 링크 수집
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

                # 상세 페이지 이동
                for idx, item in enumerate(target_items):
                    try:
                        page.goto(item['href'], timeout=60000)
                        time.sleep(1) 

                        # ▼ [수정됨] 상세 정보(후기, 평점, 좋아요) 긁어오는 로직 추가
                        extracted = page.evaluate("""() => {
                            // 1. 기본 메타 정보 (제목, 브랜드, 이미지, 가격)
                            const getMeta = (p) => document.querySelector(`meta[property="${p}"]`)?.content || "";
                            
                            // 2. [사용자 제보 기반] 정확한 태그 찾기
                            const spans = Array.from(document.querySelectorAll('span'));

                            // (1) 후기 찾기: "후기"라는 글자가 있고 + 회색 글씨(text-gray-600)인 것
                            // 예: <span class="... text-gray-600 ...">후기 11개</span>
                            let reviewCnt = 0;
                            const reviewEl = spans.find(el => el.innerText.includes('후기') && el.className.includes('text-gray-600'));
                            if (reviewEl) {
                                reviewCnt = parseInt(reviewEl.innerText.replace(/[^0-9]/g, '')) || 0;
                            }

                            // (2) 평점 찾기: 검은 글씨(text-black)이면서 + 소수점(.)이 있는 숫자
                            // 예: <span class="... text-black ...">4.9</span>
                            let ratingVal = 0.0;
                            const ratingEl = spans.find(el => 
                                el.className.includes('text-black') && 
                                /^[0-5]\.\d$/.test(el.innerText.trim()) // "4.9" 같은 형태인지 확인
                            );
                            if (ratingEl) {
                                ratingVal = parseFloat(ratingEl.innerText) || 0.0;
                            }

                            // (3) 좋아요 수 찾기: "text-body_13px_med" 클래스이면서 + 그냥 정수 숫자만 있는 것
                            // (평점은 소수점이 있어서 제외되고, 후기는 글자가 있어서 제외됨)
                            let likeCnt = 0;
                            const likeEl = spans.find(el => 
                                el.className.includes('text-body_13px_med') &&   // 폰트 클래스 일치
                                !el.className.includes('text-black') &&          // 평점(검은색) 아님
                                /^\d+$/.test(el.innerText.trim())                // 오직 숫자만 있어야 함 (예: "254")
                            );
                            if (likeEl) {
                                likeCnt = parseInt(likeEl.innerText) || 0;
                            }

                            return {
                                title: getMeta('og:title'),
                                brand: getMeta('product:brand'),
                                img: getMeta('og:image'),
                                price: getMeta('product:price:amount'),
                                review_count: reviewCnt,
                                rating: ratingVal,
                                like_count: likeCnt
                            };
                        }""")

                        price_int = int(extracted['price']) if extracted['price'] else 0
                        
                        # ▼ [수정됨] 0 대신 실제 긁어온 값 넣기
                        data = {
                            "ranking": idx + 1,
                            "brand": extracted['brand'] if extracted['brand'] else "무신사",
                            "title": extracted['title'],
                            "price": price_int,
                            "img_url": extracted['img'],
                            "category": cat_name,
                            "link": item['href'],
                            "like_count": extracted['like_count'],     # 실제 값
                            "rating": extracted['rating'],             # 실제 값
                            "review_count": extracted['review_count'], # 실제 값
                            "view_count": 0  # 조회수는 수집 불가(보통 0)
                        }
                        total_results.append(data)
                        print(f"  - 수집성공: {data['title'][:10]}... (후기:{data['review_count']}개, 평점:{data['rating']})")

                    except Exception as e:
                        print(f"  - 개별 상품 에러: {e}")
            
            except Exception as e:
                print(f"[{cat_name}] 카테고리 에러: {e}")

        browser.close()
    
    return total_results

def init_db():
    retries = 30
    while retries > 0:
        try:
            print(f">> DB 접속 시도 중... (남은 시도: {retries})")
            conn = pymysql.connect(**db_config)
            cursor = conn.cursor()
            
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
            return
            
        except pymysql.err.OperationalError as e:
            print(f"   ⏳ DB 부팅 대기 중... 3초 뒤 재시도. (에러코드: {e.args[0]})")
            time.sleep(3)
            retries -= 1
            
        except Exception as e:
            print(f"❌ 예상치 못한 에러: {e}")
            time.sleep(3)
            retries -= 1
            
    print("❌❌ DB 접속 최종 실패. 도커 로그를 확인해주세요.")
    sys.exit(1)

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
    init_db()
    crawled_data = scrape_musinsa()
    save_to_db(crawled_data)