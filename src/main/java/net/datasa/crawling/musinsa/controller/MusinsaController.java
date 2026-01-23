package net.datasa.crawling.musinsa.controller;

import lombok.RequiredArgsConstructor;
// 🔴 수정 전: import net.datasa.crawling.entity.MusinsaItem;
// 🟢 수정 후: musinsa 패키지 안에 있는 Entity 사용
import net.datasa.crawling.musinsa.entity.MusinsaItem;
import net.datasa.crawling.musinsa.service.MusinsaService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/musinsa") // 💡 중요: 모든 주소 앞에 '/musinsa'가 붙습니다.
@RequiredArgsConstructor
public class MusinsaController {

    private final MusinsaService musinsaService;

    // 접속 주소: http://localhost:9999/musinsa/crawl
    @GetMapping("/crawl")
    public String doCrawl() {
        musinsaService.crawlAndSave();
        return "<h3>[무신사] 크롤링 완료! DB 저장 성공.</h3><a href='/musinsa/ranking'>결과 확인하기</a>";
    }

    // 접속 주소: http://localhost:8080/musinsa/ranking
    @GetMapping("/ranking")
    public List<MusinsaItem> showRanking() {
        return musinsaService.getItems();
    }
}