from playwright.sync_api import sync_playwright
import sys
import time
import re

# 1. 한글 깨짐 방지
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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
    
    # 아우터까지 포함된 카테고리
    CATEGORY_URLS = {
        "상의": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=001000",
        "하의": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=003000",
        "신발": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=005000",
        "아우터": "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&categoryCode=002000"
    }

    print(">> [무신사] 통합 크롤링 시작 (스크롤 보정)...", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()

        for cat_name, cat_url in CATEGORY_URLS.items():
            print(f"\n>> 🚀 [{cat_name}] 카테고리 수집 시작...", flush=True)
            
            page.goto(cat_url, timeout=60000)
            time.sleep(2)

            # 🛠️ [추가됨] 스크롤 내리기! (상품이 다 로딩되도록)
            for _ in range(5): # 5번 정도 툭툭 내립니다
                page.keyboard.press("PageDown")
                time.sleep(0.5)
            
            # 맨 밑으로 한번 더 확 내리기
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            # 2. 링크 수집 (이제 로딩된 게 많으니 넉넉하게 80개 긁어옴)
            items_data = page.evaluate("""() => {
                const data = [];
                const links = Array.from(document.querySelectorAll("a"));
                const productLinks = links.filter(a => 
                    (a.href.includes('/goods/') || a.href.includes('/products/')) && 
                    !a.href.includes('reviews')
                );
                // 중복 제거 및 필터링을 위해 넉넉히 80개 가져옴
                productLinks.slice(0, 80).forEach(a => {
                   data.push({ href: a.href }); 
                });
                return data;
            }""")

            target_items = []
            seen = set()
            for item in items_data:
                url = item['href'].split('?')[0]
                if url not in seen:
                    seen.add(url)
                    target_items.append(item)
                if len(target_items) >= 30: break # 여기서 30개 끊기
            
            print(f">> [{cat_name}] 확보된 링크: {len(target_items)}개", flush=True)

            # 3. 상세 페이지 순회
            for idx, item in enumerate(target_items):
                try:
                    page.goto(item['href'], timeout=60000)
                    time.sleep(1.2) # 페이지 로딩 대기

                    extracted = page.evaluate("""() => {
                        const getMeta = (p) => document.querySelector(`meta[property="${p}"]`)?.content || "";
                        
                        let rating = "0";
                        let reviewCountTxt = "0";
                        const reviewBox = document.querySelector("div[data-button-id='review']");
                        if (reviewBox) {
                            const spans = reviewBox.querySelectorAll("span");
                            if (spans.length > 0) rating = spans[0].innerText;
                            if (spans.length > 1) reviewCountTxt = spans[1].innerText;
                        }

                        let likes = "0";
                        const likeIcon = document.querySelector("svg[data-mds='IcBoldLike']");
                        if (likeIcon) {
                            const container = likeIcon.closest("div");
                            if (container) { likes = container.innerText; }
                        }

                        // 서브 이미지 (사용자 요청 태그 반영)
                        let subImgs = [];
                        const bullets = document.querySelectorAll("div[class*='Pagination__Bullet'] img");
                        bullets.forEach(img => { if (img.src) subImgs.push(img.src); });
                        
                        // 구형 페이지 대비
                        if (subImgs.length === 0) {
                            const oldThumbs = document.querySelectorAll('.product_thumb img');
                            oldThumbs.forEach(img => subImgs.push(img.src));
                        }
                        const subImgString = subImgs.join(',');

                        let viewCount = "0";
                        const stats = document.querySelectorAll("#page_view"); 
                        if (stats.length > 0) viewCount = stats[0].innerText;
                        
                        return {
                            title: getMeta('og:title'),
                            brand: getMeta('product:brand'),
                            img: getMeta('og:image'),
                            price: getMeta('product:price:amount'),
                            rating: rating,
                            reviews: reviewCountTxt,
                            likes: likes,
                            sub_imgs: subImgString,
                            view_count: viewCount
                        };
                    }""")

                    final_rating = 0.0
                    try: final_rating = float(extracted['rating'])
                    except: pass

                    final_likes = parse_korean_number(extracted['likes'])
                    final_reviews = parse_korean_number(extracted['reviews'])
                    final_views = parse_korean_number(extracted['view_count'])
                    price_int = int(extracted['price']) if extracted['price'] else 0
                    brand_name = extracted['brand'] if extracted['brand'] else "무신사"

                    data = {
                        "ranking": idx + 1,
                        "brand": brand_name,
                        "title": extracted['title'],
                        "price": price_int,
                        "img_url": extracted['img'],
                        "category": cat_name, 
                        "like_count": final_likes,
                        "rating": final_rating,
                        "review_count": final_reviews,
                        "sub_img": extracted['sub_imgs'], 
                        "view_count": final_views
                    }
                    
                    total_results.append(data)
                    print(f"[{cat_name} {idx+1}] {extracted['title'][:5]}... 완료", flush=True)

                except Exception as e:
                    # 실패해도 멈추지 않고 다음 걸로 넘어감
                    print(f"[{cat_name} {idx+1}] ❌ 실패(Skip): {e}", flush=True)
            
            time.sleep(2)

        browser.close()

    return total_results

if __name__ == "__main__":
    data = scrape_musinsa()
    print(f"총 크롤링 결과: {len(data)}개")