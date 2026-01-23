package net.datasa.crawling.musinsa.dto;

import lombok.Data;

@Data
public class MusinsaItemDTO {
    private int ranking;
    private String brand;
    private String title;
    private int price;
    private String imgUrl;
    private String subImgUrl;

    // 추가 필드
    private String category;
    private int likeCount;       // JSON 키: "likeCount"
    private float rating;        // JSON 키: "rating"
    private int reviewCount;     // JSON 키: "reviewCount"
}