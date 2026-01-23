from playwright.sync_api import sync_playwright
import json
import sys
import io
import time
import re

sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

def parse_korean_number(text):
    if not text: return 0
    text = str(text).strip()
    text = text.replace(',', '')
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

def run():
    results = []
    # 랭킹 페이지
    RANKING_URL = "https://www.musinsa.com/main/musinsa/ranking?gf=A"

    print(">> [무신사] 패턴 매칭 크롤링 시작...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # 브라우저 뜨는거 확인
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # 1. 랭킹 진입
        page.goto(RANKING_URL, timeout=60000)
        time.sleep(3)

        # 2. 링크 수집
        items_data = page.evaluate("""() => {
            const data = [];
            const links = Array.from(document.querySelectorAll("a"));
            const productLinks = links.filter(a => 
                (a.href.includes('/goods/') || a.href.includes('/products/')) && 
                !a.href.includes('reviews')
            );
            productLinks.slice(0, 15).forEach(a => {
               data.push({ href: a.href }); 
            });
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
            if len(target_items) >= 10: break

        print(f">> 수집 대상: {len(target_items)}개")

        # 3. 상세 페이지 순회
        for idx, item in enumerate(target_items):
            try:
                print(f">> [{idx+1}] 접속: {item['href']}")
                page.goto(item['href'], timeout=60000)

                # 🔥 [중요] 데이터 로딩 대기 (좋아요/후기 로딩 시간 줌)
                time.sleep(4)

                # 스크롤 살짝 내려서 이미지/데이터 로딩 유도
                page.mouse.wheel(0, 1000)
                time.sleep(1)

                # ---------------------------------------------------
                # 🕵️‍♀️ 1. 기본 정보 (메타태그 - 가장 정확함)
                # ---------------------------------------------------
                meta_info = page.evaluate("""() => {
                    const getMeta = (prop) => {
                        const el = document.querySelector(`meta[property="${prop}"]`);
                        return el ? el.content : "";
                    };
                    return {
                        brand: getMeta('product:brand'),
                        title: getMeta('og:title'),
                        price: getMeta('product:price:amount'),
                        img: getMeta('og:image')
                    };
                }""")

                # ---------------------------------------------------
                # 🕵️‍♀️ 2. 통계 정보 (전체 텍스트에서 정규식으로 추출)
                # ---------------------------------------------------
                # 페이지의 모든 텍스트를 가져와서 파이썬에서 분석합니다.
                full_text = page.evaluate("document.body.innerText")

                # (1) 좋아요 찾기
                # 패턴: 줄바꿈 혹은 공백 뒤에 숫자+만/천 패턴이 있는지 확인
                # 무신사 좋아요는 보통 하트 아이콘 근처에 있지만 텍스트로는 숫자만 덩그러니 있는 경우가 많음
                # 정확도를 위해 '좋아요' 텍스트가 포함된 버튼의 텍스트를 우선적으로 가져오도록 JS 실행
                like_raw = page.evaluate("""() => {
                    // 1. '좋아요' 단어가 포함된 요소 찾기
                    const likes = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.innerText && el.innerText.includes('좋아요') && el.innerText.length < 30)
                        .map(el => el.innerText);
                    
                    // 2. 만약 없다면 class에 like가 들어간 요소의 숫자 찾기
                    if (likes.length === 0) {
                         const likeClass = Array.from(document.querySelectorAll('[class*="like"]'))
                            .filter(el => el.innerText && el.innerText.match(/[0-9]/) && el.innerText.length < 10)
                            .map(el => el.innerText);
                         return likeClass[0] || "0";
                    }
                    return likes[0] || "0";
                }""")

                # (2) 별점 찾기 (텍스트에서 "4.8" "4.9" 같은 패턴 찾기)
                # ★ 모양이 있거나 점수가 있는 패턴
                rating = 0.0
                rating_match = re.search(r'([3-5])\.([0-9])', full_text) # 3.0 ~ 5.9 사이 숫자 검색
                if rating_match:
                    rating = float(rating_match.group(0))

                # (3) 후기 수 찾기 ("후기 1,234" 또는 "후기 1.2만")
                review_cnt = 0
                # "후기" 라는 글자 뒤에 나오는 숫자 찾기
                review_match = re.search(r'후기\s*([0-9,만천]+)', full_text)
                if review_match:
                    review_cnt = parse_korean_number(review_match.group(1))
                else:
                    # 못 찾았으면 숫자+개 패턴 ("2,392개")
                    review_match2 = re.search(r'([0-9,]+)개', full_text)
                    if review_match2:
                        review_cnt = parse_korean_number(review_match2.group(1))

                # --- 데이터 정리 ---
                price = int(float(meta_info['price'])) if meta_info['price'] else 0
                brand = meta_info['brand'] if meta_info['brand'] else "무신사"
                title = meta_info['title'] if meta_info['title'] else "제목 없음"

                # 좋아요 숫자 정제
                like_cnt = parse_korean_number(like_raw)

                # 후기가 0이면 혹시 모르니 rating도 의심 (둘 다 없으면 신상품일수도)
                if review_cnt == 0 and rating == 0:
                    # 안전장치: 전체 텍스트에서 (123) 처럼 괄호 안 숫자 찾기 (댓글수일 확률 높음)
                    backup_match = re.search(r'\(([0-9,]+)\)', full_text)
                    if backup_match:
                        review_cnt = parse_korean_number(backup_match.group(1))

                data = {
                    "ranking": idx + 1,
                    "brand": brand,
                    "title": title,
                    "price": price,
                    "imgUrl": meta_info['img'],
                    "subImgUrl": meta_info['img'],
                    "category": "의류",
                    "likeCount": like_cnt,
                    "rating": rating,
                    "reviewCount": review_cnt
                }

                results.append(data)
                print(f"   -> [확인] ❤️{like_cnt} | ★{rating} | 📝{review_cnt} | {title[:10]}")

            except Exception as e:
                print(f"   -> ❌ 에러: {e}")

        browser.close()

    print(f">> 최종 {len(results)}건 저장.")
    with open("python/musinsa_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    run()