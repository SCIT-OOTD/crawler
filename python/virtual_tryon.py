import os
import json
import torch
import cv2
import numpy as np
import requests
from PIL import Image
from io import BytesIO
from diffusers import AutoPipelineForInpainting
from diffusers.utils import load_image

# ==========================================
# 1. 설정 (Configuration)
# ==========================================
# 저장된 JSON 파일 경로 (또는 DB 연결 정보를 쓰셔도 됩니다)
DATA_FILE = 'twentynine_ai_data.json'
OUTPUT_DIR = 'tryon_results'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 모델 ID (CatVTON 기반 또는 호환되는 인페인팅 모델 사용)
# CatVTON 전용 파이프라인은 복잡하므로, 가장 유사한 고성능 인페인팅 모델을 먼저 예시로 듭니다.
# 실제 CatVTON 가중치를 쓰려면 전용 repo를 clone해야 하므로, 여기선 diffusers 표준 방식으로 구현합니다.
MODEL_ID = "kandinsky-community/kandinsky-2-2-decoder-inpaint" # 혹은 CatVTON 경로

# ==========================================
# 2. 유틸리티 함수
# ==========================================
def download_image(url):
    """URL에서 이미지를 다운로드하여 PIL 포맷으로 변환"""
    response = requests.get(url)
    return Image.open(BytesIO(response.content)).convert("RGB")

def create_upper_body_mask(image_pil):
    """
    [핵심] 옷을 입힐 영역(Mask)을 자동으로 만듭니다.
    원래는 'Segmentation' 모델을 써야 하지만, 여기선 테스트를 위해
    이미지의 중앙 부분을 마스크로 잡는 간단한 방식을 사용합니다.
    """
    w, h = image_pil.size
    mask = np.zeros((h, w), dtype=np.uint8)

    # 예시: 상체 부분(위에서 15%~60% 지점)에 네모난 구멍을 뚫음
    # 실제 서비스에선 'DensePose'나 'Human Parsing' AI를 써야 정확합니다.
    cv2.rectangle(mask, (int(w*0.2), int(h*0.15)), (int(w*0.8), int(h*0.6)), 255, -1)

    return Image.fromarray(mask)

# ==========================================
# 3. 메인 로직
# ==========================================
def run_virtual_tryon():
    print(">> [1] 모델 로딩 중... (GPU 필요)")
    try:
        # GPU 사용 설정
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32

        # 파이프라인 로드 (처음 실행 시 몇 기가바이트 다운로드함)
        pipe = AutoPipelineForInpainting.from_pretrained(
            "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
            torch_dtype=dtype,
            variant="fp16" if device == "cuda" else None
        ).to(device)
        print(f">> 모델 로딩 완료 (Device: {device})")

    except Exception as e:
        print(f"🚨 모델 로딩 실패: {e}")
        print("GPU 메모리가 부족하거나 라이브러리 버전 문제일 수 있습니다.")
        return

    # 데이터 로드
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        products = json.load(f)

    if not products:
        print("데이터가 없습니다.")
        return

    # 첫 번째 상품으로 테스트
    item = products[0]
    print(f">> [2] 처리할 상품: {item['title']}")

    try:
        # 이미지 다운로드
        model_img = download_image(item['model_img']) # 사람
        cloth_img = download_image(item['cloth_img']) # 옷

        # 이미지 크기 조정 (512x512, 1024x1024 등 8의 배수여야 함)
        model_img = model_img.resize((1024, 1024))
        cloth_img = cloth_img.resize((1024, 1024))

        # 마스크 생성 (옷을 입힐 위치)
        mask_img = create_upper_body_mask(model_img)

        # 결과 저장 확인용
        model_img.save(os.path.join(OUTPUT_DIR, "input_person.jpg"))
        cloth_img.save(os.path.join(OUTPUT_DIR, "input_cloth.jpg"))
        mask_img.save(os.path.join(OUTPUT_DIR, "input_mask.jpg"))

        print(">> [3] 가상 피팅 생성 시작 (약 10~30초 소요)...")

        # 프롬프트 생성 (옷의 특징을 텍스트로도 줌)
        prompt = f"A photo of a model wearing {item['title']}, high quality, photorealistic"

        # 추론 실행
        # (참고: CatVTON 전용 파이프라인은 cloth_image를 별도 입력으로 받지만,
        # 일반 인페인팅 모델은 텍스트+마스크 기반이므로 여기서는 개념적 구현입니다.)
        image = pipe(
            prompt=prompt,
            image=model_img,
            mask_image=mask_img,
            num_inference_steps=30,
            strength=0.99, # 마스크 영역을 얼마나 많이 바꿀지 (0.99 = 완전히 교체)
            guidance_scale=7.5
        ).images[0]

        # 결과 저장
        save_path = os.path.join(OUTPUT_DIR, f"result_{item['product_no']}.png")
        image.save(save_path)
        print(f"✅ 생성 완료! 저장됨: {save_path}")

    except Exception as e:
        print(f"🚨 에러 발생: {e}")

if __name__ == "__main__":
    run_virtual_tryon()