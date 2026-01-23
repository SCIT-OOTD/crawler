import sys
import io
import json
import os
import time
import random

# ★ 중요: 일반 selenium 대신 undetected_chromedriver 사용
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# 한글 깨짐 방지
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

def crawl_pc_stealth():
    # 29CM 남성 의류 (PC 주소)
    list_url = "https://www.29cm.co.kr/store/category/list?categoryLargeCode=272100100&categoryMediumCode=272103100"

    print(">> [PC 스텔스 모드] 데스크탑 환경에서 차단을 우회합니다...")

    data_list = []
    driver = None

    try:
        # 1. 보안 우회 브라우저 설정 (모바일 설정 X)
        options = uc.ChromeOptions()
        # options.add_argument('--headless') # 화면 보고 싶으면 주석 유지
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        # 브라우저 실행 (버전 자동 매칭)
        driver = uc.Chrome(options=options, version_main=None)

        # ★ 화면을 넓게 써야 PC 레이아웃이 나옴
        driver.set_window_size(1920, 1080)

        print(f">> PC 페이지 접속: {list_url}")
        driver.get(list_url)

        # 2. 로딩 대기 (PC는 로딩이 좀 더 걸릴 수 있음)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/product/']"))
            )
            print(">> 상품 목록 로딩 성공!")
        except:
            print("🚨 [차단 감지] PC 버전 접속이 차단되었습니다. IP 변경(핫스팟)이 필요합니다.")
            driver.save_screenshot("pc_block_error.png")
            return []

        # 스크롤 내려서 데이터 로딩
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        # 3. 상품 링크 수집
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        anchors = soup.find_all('a', href=True)

        product_urls = []
        seen_ids = set()

        for a in anchors:
            href = a['href']
            if '/product/' in href:
                # https://product.29cm.co.kr/... 형태 처리
                if href.startswith('http'): full_url = href
                else: full_url = "https://www.29cm.co.kr" + href

                p_id = full_url.split('/')[-1].split('?')[0]
                if p_id.isdigit() and p_id not in seen_ids:
                    product_urls.append(full_url)
                    seen_ids.add(p_id)

        # 상위 6개만 테스트 (아메스 포함 확인용)
        target_urls = product_urls[:6]
        print(f">> 수집 대상: {len(target_urls)}개")

        # 4. 상세 페이지 순회
        for i, p_url in enumerate(target_urls):
            try:
                print(f" -> [{i+1}] 상세 진입: {p_url}")
                driver.get(p_url)

                # 이미지 슬라이더 로딩 대기 (PC는 이미지가 큼)
                time.sleep(random.uniform(2.5, 4))

                detail_soup = BeautifulSoup(driver.page_source, 'html.parser')

                # (1) 브랜드/제목
                brand = "29CM"
                title = "Unknown"
                og_title = detail_soup.find("meta", property="og:title")
                if og_title:
                    content = og_title["content"]
                    if ']' in content:
                        parts = content.split(']')
                        brand = parts[0].replace('[', '').strip()
                        title = parts[1].strip()
                    else:
                        title = content

                # (2) 가격
                price = 0
                text = detail_soup.get_text()
                import re
                matches = re.findall(r'([\d,]+)원', text)
                for m in matches:
                    p = int(m.replace(',', ''))
                    if p > 1000:
                        price = p
                        break

                # (3) 이미지 분리 (PC 버전 로직)
                valid_imgs = []
                imgs = detail_soup.find_all('img')

                for img in imgs:
                    src = img.get('src', '')
                    if not src: continue
                    if not src.startswith('http'): src = "https:" + src

                    # 썸네일 제외, 메인 이미지만
                    if ('/item/' in src or '/product/' in src) and '.svg' not in src:
                        if '60x60' not in src and '50x50' not in src:
                            if src not in valid_imgs:
                                valid_imgs.append(src)

                model_img = ""
                cloth_img = ""

                # [필승 로직] 0번: 모델, 1번: 옷
                if len(valid_imgs) >= 2:
                    model_img = valid_imgs[0]
                    cloth_img = valid_imgs[1]
                elif len(valid_imgs) == 1:
                    model_img = valid_imgs[0]
                    cloth_img = valid_imgs[0]

                print(f"    - 모델: {model_img[-20:]}")
                print(f"    - 옷  : {cloth_img[-20:]}")

                obj = {
                    "product_no": p_url.split('/')[-1].split('?')[0],
                    "source": "29CM_PC",
                    "brand": brand,
                    "title": title,
                    "price": price,
                    "cloth_img": cloth_img,
                    "model_img": model_img
                }
                data_list.append(obj)

            except Exception as e:
                print(f"Error: {e}")
                continue

    except Exception as e:
        print(f"Fatal Error: {e}")
    finally:
        if driver: driver.quit()

    return data_list

if __name__ == "__main__":
    result = crawl_pc_stealth()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(current_dir, 'twentynine_ai_data.json')

    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)