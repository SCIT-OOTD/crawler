from playwright.sync_api import sync_playwright
import sys
import time
import re
import pymysql

# 1. DB 설정
db_config = {
    'host': 'mysql-container',   # docker-compose 서비스 이름
    'user': 'root',
    'password': '1234',
    'database': 'musinsa_db',
    'port': 3306,
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def scrape_musinsa():
    total_results = []
    # 카테고리 정의
    CATEGORY_URLS = {
        "상의": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=001000",
        "하의": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=003000",
        "신발": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=005000",
        "아우터": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=002000"
    }

    print(">> [무신사] 대규모 크롤링 시작 (카테고리별 100개)...", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 100개 긁는 동안 타임아웃 나지 않게 설정
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.set_default_timeout(60000) # 60초

        for cat_name, cat_url in CATEGORY_URLS.items():
            print(f"\n>> 🚀 [{cat_name}] 리스트 확보 시작...", flush=True)
            try:
                page.goto(cat_url)
                time.sleep(2)

                # ---------------------------------------------------------
                # [핵심] 100개 모일 때까지 스크롤 내리기 (강력한 로직)
                # ---------------------------------------------------------
                target_count = 100
                prev_count = 0
                scroll_attempts = 0
                max_attempts = 30  # 최대 30번 스크롤 시도

                while True:
                    # 현재 화면에 로딩된 상품 링크 개수 세기 (중복 제거 전 단순 개수)
                    # 무신사는 한 상품에 링크가 여러 개일 수 있어서 넉넉하게 봅니다.
                    page.keyboard.press("End")
                    time.sleep(1.5) # 로딩 대기

                    # 실제 유니크한 상품 링크 개수 계산
                    unique_count = page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll("a"));
                        const goodsLinks = links
                            .map(a => a.href)
                            .filter(href => (href.includes('/goods/') || href.includes('/products/')) && !href.includes('reviews'));
                        
                        // 주소에서 ? 뒤에 파라미터 떼고 중복 제거해서 숫자 세기
                        const uniqueSet = new Set(goodsLinks.map(url => url.split('?')[0]));
                        return uniqueSet.size;
                    }""")
                    
                    print(f"   Now: 상품 {unique_count}개 발견... (스크롤 중)", flush=True)

                    if unique_count >= target_count:
                        print(f"   ✅ 목표 달성! ({unique_count}개)")
                        break
                    
                    if unique_count == prev_count:
                        scroll_attempts += 1
                        if scroll_attempts >= 5: # 5번 연속으로 개수가 안 늘어나면 끝으로 간주
                            print("   ⚠️ 더 이상 상품이 없습니다.")
                            break
                    else:
                        scroll_attempts = 0 # 개수가 늘어났으면 카운트 초기화
                    
                    prev_count = unique_count
                    
                    if scroll_attempts > max_attempts:
                        break

                # ---------------------------------------------------------
                # 링크 추출
                # ---------------------------------------------------------
                items_data = page.evaluate("""() => {
                    const data = [];
                    const links = Array.from(document.querySelectorAll("a"));
                    const productLinks = links.filter(a => 
                        (a.href.includes('/goods/') || a.href.includes('/products/')) && 
                        !a.href.includes('reviews')
                    );
                    productLinks.forEach(a => { data.push({ href: a.href }); });
                    return data;
                }""")

                # 파이썬에서 중복 제거하고 100개 자르기
                target_items = []
                seen = set()
                for item in items_data:
                    url = item['href'].split('?')[0]
                    if url not in seen:
                        seen.add(url)
                        target_items.append(item)
                
                # 딱 100개만 남기기
                target_items = target_items[:100]
                print(f"   - 실제 수집할 링크: {len(target_items)}개")

                # ---------------------------------------------------------
                # 상세 페이지 순회
                # ---------------------------------------------------------
                for idx, item in enumerate(target_items):
                    try:
                        page.goto(item['href'])
                        time.sleep(0.5) 

                        extracted = page.evaluate("""() => {
                            const getMeta = (p) => document.querySelector(`meta[property="${p}"]`)?.content || "";
                            const spans = Array.from(document.querySelectorAll('span'));

                            // 후기
                            let reviewCnt = 0;
                            const reviewEl = spans.find(el => el.innerText.includes('후기') && el.className.includes('text-gray-600'));
                            if (reviewEl) reviewCnt = parseInt(reviewEl.innerText.replace(/[^0-9]/g, '')) || 0;

                            // 평점
                            let ratingVal = 0.0;
                            const ratingEl = spans.find(el => el.className.includes('text-black') && /^[0-5]\\.\\d$/.test(el.innerText.trim()));
                            if (ratingEl) ratingVal = parseFloat(ratingEl.innerText) || 0.0;

                            // 좋아요
                            let likeCnt = 0;
                            const likeEl = spans.find(el => el.className.includes('text-body_13px_med') && !el.className.includes('text-black') && /^\\d+$/.test(el.innerText.trim()));
                            if (likeEl) likeCnt = parseInt(likeEl.innerText) || 0;

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
                        
                        data = {
                            "ranking": idx + 1,
                            "brand": extracted['brand'] if extracted['brand'] else "무신사",
                            "title": extracted['title'],
                            "price": price_int,
                            "img_url": extracted['img'],
                            "category": cat_name,
                            "link": item['href'],
                            "like_count": extracted['like_count'],
                            "rating": extracted['rating'],
                            "review_count": extracted['review_count'],
                            "view_count": 0
                        }
                        total_results.append(data)
                        
                        if (idx + 1) % 10 == 0:
                            print(f"     [{cat_name}] {idx + 1}/100 완료...")

                    except Exception as e:
                        print(f"     X 개별 상품 에러: {e}")
            
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
            print(">> ✅ DB 연결 완료!")
            conn.close()
            return
        except Exception as e:
            print(f"   ⏳ DB 대기 중... ({e})")
            time.sleep(3)
            retries -= 1
    sys.exit(1)

def save_to_db(items):
    if not items: return
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
                item['title'], item['brand'], item['price'], item['img_url'], 
                item['category'], item.get('link', '#'), item['ranking'],
                item['like_count'], item['rating'], item['review_count'], item['view_count']
            ))
        conn.commit()
        print(f">> ✅ DB 저장 완료!")
    except Exception as e:
        print(f"❌ 저장 에러: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    # 혹시 이 파일을 직접 실행할 때를 대비해 둠
    init_db()
    crawled_data = scrape_musinsa()
    save_to_db(crawled_data)