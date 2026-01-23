from playwright.sync_api import sync_playwright
import json
import sys
import io
import time
import re

# 1. 한글 깨짐 방지
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

def parse_korean_number(text):
    """ '9.2만' -> 92000, '6,159개' -> 6159 변환 """
    if not text: return 0
    text = str(text).strip()
    multiplier = 1
    
    if '만' in text:
        multiplier = 10000
        text = text.replace('만', '')
    elif '천' in text:
        multiplier = 1000
        text = text.replace('천', '')
    
    # 숫자와 점(.)만 남기고 제거 (콤마, '개', '후기' 등 제거)
    clean_num = re.sub(r"[^0-9.]", "", text)
    if clean_num:
        try:
            return int(float(clean_num) * multiplier)
        except:
            return 0
    return 0

def run():
    results = []
    
    # ✅ 상의(Top) 랭킹 URL
    RANKING_URL = "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&contentsId=&categoryCode=001000&ageBand=AGE_BAND_ALL&subPan=product"

    print(">> [무신사] 구조 기반 정밀 크롤링 시작 (상의 TOP 20)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. 랭킹 페이지 접속
        page.goto(RANKING_URL, timeout=60000)
        time.sleep(3)

        # 2. 링크 수집
        items_data = page.evaluate("""() => {
            const data = [];
            const links = Array.from(document.querySelectorAll("a"));
            // 상품 링크만 필터링
            const productLinks = links.filter(a => 
                (a.href.includes('/goods/') || a.href.includes('/products/')) && 
                !a.href.includes('reviews')
            );
            productLinks.slice(0, 30).forEach(a => {
               data.push({ href: a.href }); 
            });
            return data;
        }""")

        # 중복 제거 및 20개 제한
        target_items = []
        seen = set()
        for item in items_data:
            url = item['href'].split('?')[0]
            if url not in seen:
                seen.add(url)
                target_items.append(item)
            if len(target_items) >= 20: break
        
        print(f">> 수집 대상: {len(target_items)}개")

        # 3. 상세 페이지 순회
        for idx, item in enumerate(target_items):
            try:
                print(f">> [{idx+1}/20] 이동: {item['href']}")
                page.goto(item['href'], timeout=60000)
                time.sleep(1.5) # 로딩 대기

                # ---------------------------------------------------
                # 🕵️‍♀️ [핵심 전략] 보내주신 HTML 태그 정밀 타격
                # ---------------------------------------------------
                extracted = page.evaluate("""() => {
                    // 1. 평점 & 후기 찾기
                    // 힌트: <div ... data-button-id="review">
                    let rating = "0";
                    let reviewCountTxt = "0";
                    
                    const reviewBox = document.querySelector("div[data-button-id='review']");
                    if (reviewBox) {
                        const spans = reviewBox.querySelectorAll("span");
                        // 첫 번째 span: 평점 (4.8)
                        if (spans.length > 0) rating = spans[0].innerText;
                        // 두 번째 span: 후기 개수 (후기 6,159개)
                        if (spans.length > 1) reviewCountTxt = spans[1].innerText;
                    }

                    // 2. 좋아요 찾기
                    // 힌트: <svg ... data-mds="IcBoldLike"> 가 있는 곳 옆의 텍스트
                    let likes = "0";
                    // 아이콘을 먼저 찾음
                    const likeIcon = document.querySelector("svg[data-mds='IcBoldLike']");
                    
                    if (likeIcon) {
                        // 아이콘의 부모(버튼)의 부모(div) 전체 텍스트를 가져오거나
                        // 아이콘 근처의 span을 찾음
                        // 가장 확실한 방법: 아이콘이 포함된 가장 가까운 컨테이너 div를 찾고 그 안의 텍스트 추출
                        const container = likeIcon.closest("div"); // <div class="Like__Container...">
                        if (container) {
                            likes = container.innerText; 
                        }
                    }

                    // 3. 메타 정보 (제목, 가격, 이미지)
                    const getMeta = (p) => document.querySelector(`meta[property="${p}"]`)?.content || "";
                    
                    return {
                        title: getMeta('og:title'),
                        brand: getMeta('product:brand'),
                        img: getMeta('og:image'),
                        price: getMeta('product:price:amount'),
                        rating: rating,
                        reviews: reviewCountTxt,
                        likes: likes
                    };
                }""")

                # 4. 데이터 정제 (Python)
                final_rating = 0.0
                try:
                    final_rating = float(extracted['rating'])
                except:
                    pass

                final_likes = parse_korean_number(extracted['likes'])
                final_reviews = parse_korean_number(extracted['reviews'])
                price_int = int(extracted['price']) if extracted['price'] else 0
                brand_name = extracted['brand'] if extracted['brand'] else "무신사"

                data = {
                    "ranking": idx + 1,
                    "brand": brand_name,
                    "title": extracted['title'],
                    "price": price_int,
                    "imgUrl": extracted['img'],
                    "subImgUrl": extracted['img'],
                    "category": "상의", 
                    "likeCount": final_likes,
                    "rating": final_rating,
                    "reviewCount": final_reviews 
                }
                
                results.append(data)
                print(f"   -> [성공] ❤️{final_likes} | ★{final_rating} | 📝{final_reviews} | {extracted['title'][:10]}...")

            except Exception as e:
                print(f"   -> ❌ 실패: {e}")

        browser.close()

    # 5. 저장
    with open("python/musinsa_data_tag.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f">> 최종 {len(results)}건 저장 완료.")

if __name__ == "__main__":
    run()