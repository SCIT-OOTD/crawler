package net.datasa.crawling.musinsa.entity;

import jakarta.persistence.*;
import lombok.Data;

@Entity
@Table(name = "musinsa_item")
@Data
public class MusinsaItem {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Integer ranking;
    private String brand;
    private String title;
    private Integer price;

    @Column(length = 2000)
    private String imgUrl;
    @Column(length = 2000)
    private String subImgUrl;

    // --- 추가 정보 ---
    private String category;

    // 🆕 좋아요, 별점, 후기
    private Integer likeCount;   // 좋아요 수
    private Float rating;        // 별점 (4.9 등 소수점)
    private Integer reviewCount; // 후기 수
}