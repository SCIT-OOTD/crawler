package net.datasa.crawling.twentynine.repository;

import net.datasa.crawling.twentynine.entity.TwentyNineItem;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional; // 이거 import 필요

public interface TwentyNineRepository extends JpaRepository<TwentyNineItem, Long> {

    // ★ 이 줄을 추가하세요! (상품번호로 데이터 찾기)
    Optional<TwentyNineItem> findByProductNo(String productNo);
}