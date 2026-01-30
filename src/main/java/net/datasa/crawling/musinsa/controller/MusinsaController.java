package net.datasa.crawling.musinsa.controller;

import org.springframework.core.io.ClassPathResource;
import org.springframework.http.MediaType;
import org.springframework.util.StreamUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

@RestController
@RequestMapping("/musinsa")
public class MusinsaController {

    // 접속 주소: http://localhost:9999/musinsa/view
    @GetMapping(value = "/view", produces = MediaType.TEXT_HTML_VALUE)
    public String showHtml() {
        try {
            // 👇 [핵심 변경] 이미지를 보니 'templates' 폴더 안에 있습니다.
            // static -> templates 로 단어만 바꿨습니다.
            ClassPathResource resource = new ClassPathResource("templates/index.html");
            
            // 파일이 존재하면 읽어서 글자(HTML)로 돌려줍니다.
            return StreamUtils.copyToString(resource.getInputStream(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            return "<h1>에러! templates 폴더 안에 index.html 파일을 못 찾겠어요.</h1><br>" + e.getMessage();
        }
    }
}