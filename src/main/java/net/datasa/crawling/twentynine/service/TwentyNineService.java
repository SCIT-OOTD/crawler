package net.datasa.crawling.twentynine.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import net.datasa.crawling.twentynine.entity.TwentyNineItem;
import net.datasa.crawling.twentynine.repository.TwentyNineRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.util.Arrays;
import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional
public class TwentyNineService {

    private final TwentyNineRepository repository;

    // 1. 파이썬 경로 설정 (본인 PC 경로 확인 필수)
    private static final String PYTHON_ENV_PATH = "C:\\Users\\user\\miniconda3\\envs\\crawling\\python.exe";

    // 2. 파일 경로 설정
    private static final String PROJECT_PATH = System.getProperty("user.dir");
    private static final String PYTHON_SCRIPT_PATH = PROJECT_PATH + "\\python\\twentynine.py";
    private static final String JSON_FILE_PATH = PROJECT_PATH + "\\python\\twentynine_ai_data.json";

    /**
     * A. 크롤링 실행 및 DB 저장/업데이트 (Upsert)
     */
    public void runCrawling() {
        System.out.println("🚀 [Java] 29CM 크롤링 서비스 시작...");

        try {
            // 파이썬 실행
            ProcessBuilder pb = new ProcessBuilder(PYTHON_ENV_PATH, PYTHON_SCRIPT_PATH);
            pb.redirectErrorStream(true);
            Process process = pb.start();

            // 로그 출력 (UTF-8)
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), "UTF-8"));
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println("[Python] " + line);
            }
            process.waitFor();

            // JSON 읽기
            File jsonFile = new File(JSON_FILE_PATH);
            if (!jsonFile.exists()) {
                System.err.println("❌ JSON 파일 없음: " + JSON_FILE_PATH);
                return;
            }

            ObjectMapper mapper = new ObjectMapper();
            List<TwentyNineItem> items = Arrays.asList(mapper.readValue(jsonFile, TwentyNineItem[].class));

            if (!items.isEmpty()) {
                // 중복 방지 저장 로직
                for (TwentyNineItem item : items) {
                    TwentyNineItem existingItem = repository.findByProductNo(item.getProductNo())
                            .orElse(null);

                    if (existingItem != null) {
                        // 업데이트
                        existingItem.setBrand(item.getBrand());
                        existingItem.setTitle(item.getTitle());
                        existingItem.setPrice(item.getPrice());
                        existingItem.setClothImg(item.getClothImg());
                        existingItem.setModelImg(item.getModelImg());
                        repository.save(existingItem);
                    } else {
                        // 신규 저장
                        repository.save(item);
                    }
                }
                System.out.println("💾 DB 동기화 완료: " + items.size() + "개");
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    /**
     * B. DB에 저장된 데이터 조회 (Controller에서 호출하는 메소드)
     * ★ 이 부분이 없어서 에러가 났던 것입니다.
     */
    public List<TwentyNineItem> getCrawledData() {
        return repository.findAll();
    }
}