package net.datasa.crawling.twentynine.entity;

import jakarta.persistence.*;
import lombok.Data;
// ★ 이 import 문을 꼭 추가하세요!
import com.fasterxml.jackson.annotation.JsonProperty;

@Data
@Entity
@Table(name = "twentynine_item")
public class TwentyNineItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // ★ [수정 1] JSON의 "product_no"를 자바의 "productNo"와 연결
    @JsonProperty("product_no")
    @Column(name = "product_no")
    private String productNo;

    // (source는 이름이 같아서 괜찮음)
    private String source;

    // (brand는 이름이 같아서 괜찮음)
    private String brand;

    // (title은 이름이 같아서 괜찮음)
    private String title;

    // (price는 이름이 같아서 괜찮음)
    private int price;

    // ★ [수정 2] JSON의 "cloth_img"를 연결
    @JsonProperty("cloth_img")
    @Column(name = "cloth_img")
    private String clothImg;

    // ★ [수정 3] JSON의 "model_img"를 연결
    @JsonProperty("model_img")
    @Column(name = "model_img")
    private String modelImg;
}