package net.datasa.crawling.twentynine.dto;

import lombok.Data;

@Data
public class TwentyNineDTO {
    private String source;      // "29CM"
    private String product_no;  // 품번
    private String brand;       // 브랜드
    private String title;       // 상품명
    private int price;          // 가격
    private String clothImg;    // 옷 사진 URL
    private String modelImg;    // 모델 사진 URL
}