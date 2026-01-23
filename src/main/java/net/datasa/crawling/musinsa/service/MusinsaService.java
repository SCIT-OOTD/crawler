package net.datasa.crawling.musinsa.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import net.datasa.crawling.musinsa.dto.MusinsaItemDTO;
import net.datasa.crawling.musinsa.entity.MusinsaItem;
import net.datasa.crawling.musinsa.repository.MusinsaRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional
public class MusinsaService {

    private final MusinsaRepository musinsaRepository;

    public void crawlAndSave() {
        try {
            System.out.println("🐍 [무신사] 파이썬 크롤링 프로세스 시작...");

            // 1. 경로 설정 (본인 환경에 맞게 수정 필요)
            // 파이썬 실행 명령어 (윈도우는 보통 "python", 맥/리눅스는 "python3")
            String pythonExe = "python"; 
            
            // 실행할 파이썬 스크립트 경로 (프로젝트 루트 기준 상대 경로 추천)
            // 만약 절대경로를 쓰신다면: "C:\\teamproject\\crawler\\python\\musinsa.py"
            String scriptPath = "python/musinsa.py"; 

            // 파이썬이 결과물을 저장할 파일 경로 (파이썬 코드의 open(...) 안의 경로와 똑같아야 함!)
            // 아까 제가 드린 코드는 "musinsa_data_tag.json"으로 저장하게 되어있습니다.
            String jsonFilePath = "python/musinsa_data_tag.json"; 

            // 2. 프로세스 빌더 설정
            ProcessBuilder pb = new ProcessBuilder(pythonExe, scriptPath);
            pb.directory(new File(System.getProperty("user.dir"))); // 프로젝트 루트 폴더에서 실행
            
            // 3. 프로세스 시작
            Process process = pb.start();

            pb.environment().put("PYTHONIOENCODING", "utf-8");

            // ----------------------------------------------------------------
            // 🔥 [중요] 파이썬의 출력(로그)와 에러를 실시간으로 읽어오기
            //    이 부분이 없으면 파이썬이 왜 죽었는지 알 수 없습니다.
            // ----------------------------------------------------------------
            BufferedReader stdOut = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
            BufferedReader stdErr = new BufferedReader(new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8));

            String line;
            while ((line = stdOut.readLine()) != null) {
                System.out.println("[Python Log] " + line); // 파이썬의 print() 내용
            }
            while ((line = stdErr.readLine()) != null) {
                System.err.println("[Python Error] " + line); // 파이썬 에러 메시지
            }

            // 4. 종료 대기
            int exitCode = process.waitFor();
            if (exitCode != 0) {
                throw new RuntimeException("파이썬 스크립트가 비정상 종료되었습니다. (종료코드: " + exitCode + ")");
            }

            // 5. 결과 파일 확인
            File file = new File(jsonFilePath);
            if (!file.exists() || file.length() == 0) {
                throw new RuntimeException("크롤링 결과 파일(" + jsonFilePath + ")이 생성되지 않았거나 비어있습니다. 파이썬 로그를 확인하세요.");
            }

            // 6. JSON 읽기 및 매핑
            ObjectMapper mapper = new ObjectMapper();
            // (혹시 DTO에 없는 필드가 JSON에 있어도 에러 안 나게 설정)
            mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

            List<MusinsaItemDTO> dtoList = mapper.readValue(file, new TypeReference<List<MusinsaItemDTO>>() {});

            if (dtoList.isEmpty()) {
                System.out.println("⚠️ 수집된 데이터가 0건입니다.");
                return;
            }

            // 7. DTO -> Entity 변환
            List<MusinsaItem> entityList = new ArrayList<>();
            for (MusinsaItemDTO dto : dtoList) {
                MusinsaItem entity = new MusinsaItem();

                entity.setRanking(dto.getRanking());
                entity.setBrand(dto.getBrand());
                entity.setTitle(dto.getTitle());
                entity.setPrice(dto.getPrice());
                entity.setImgUrl(dto.getImgUrl());
                
                // subImgUrl이 없을 경우 메인 이미지로 대체하거나 null 처리
                entity.setSubImgUrl(dto.getSubImgUrl() != null ? dto.getSubImgUrl() : dto.getImgUrl());

                entity.setCategory(dto.getCategory() != null ? dto.getCategory() : "의류"); // 기본값
                entity.setLikeCount(dto.getLikeCount());
                entity.setRating(dto.getRating());
                entity.setReviewCount(dto.getReviewCount());

                entityList.add(entity);
            }

            // 8. DB 저장
            musinsaRepository.deleteAll(); // 기존 데이터 삭제 (필요시 주석 처리)
            musinsaRepository.saveAll(entityList);

            System.out.println("✅ [무신사] 최종 DB 저장 완료: " + entityList.size() + "건");

        } catch (Exception e) {
            e.printStackTrace();
            throw new RuntimeException("크롤링 서비스 오류: " + e.getMessage());
        }
    }

    public List<MusinsaItem> getItems() {
        return musinsaRepository.findAll();
    }
}