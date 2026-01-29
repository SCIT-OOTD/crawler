package net.datasa.crawling.musinsa.controller;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import net.datasa.crawling.musinsa.entity.MusinsaItem;
import net.datasa.crawling.musinsa.service.MusinsaService;

@RestController
@RequestMapping("/musinsa")
@RequiredArgsConstructor
public class MusinsaController {

    private final MusinsaService musinsaService;

    // 1. 크롤링 버튼
    @GetMapping("/crawl")
    public String doCrawl() {
        musinsaService.crawlAndSave();
        return "<h3>크롤링 완료!</h3><br><a href='/musinsa/view'>👉 화면 보러가기</a>";
    }

    // 2. 데이터 조회 (JSON)
    @GetMapping("/ranking")
    public List<MusinsaItem> showRanking() {
        return musinsaService.getItems();
    }

    // 3. HTML 화면 띄우기 (무조건 성공하는 코드)
    // 접속 주소: http://localhost:8080/musinsa/view
    @GetMapping(value = "/view", produces = MediaType.TEXT_HTML_VALUE)
    public String showHtml() {
        try {
            // 프로젝트 최상위 폴더(pom.xml 옆)에 있는 index.html을 읽음
            return Files.readString(Paths.get("index.html"));
        } catch (IOException e) {
            return "<h1>index.html 파일이 없습니다. pom.xml 옆에 두셨나요?</h1>";
        }
    }
}