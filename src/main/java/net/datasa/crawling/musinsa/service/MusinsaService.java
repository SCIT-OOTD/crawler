package net.datasa.crawling.musinsa.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import net.datasa.crawling.musinsa.dto.MusinsaItemDTO;
import net.datasa.crawling.musinsa.entity.MusinsaItem;
import net.datasa.crawling.musinsa.repository.MusinsaRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional
public class MusinsaService {

    private final MusinsaRepository musinsaRepository;

    public void crawlAndSave() {
       
        String pythonPath = "python"; 

        // 2. 실행할 파이썬 스크립트의 '절대 경로' (상대 경로보다 안전함)
        String scriptPath = "C:\\teamproject\\crawler\\python\\musinsa.py";
        try {
            System.out.println("🐍 [무신사] 파이썬 크롤링 시작...");

            ProcessBuilder pb = new ProcessBuilder(pythonPath, scriptPath);
            pb.inheritIO(); // 콘솔에 로그 출력
            Process process = pb.start();

            int exitCode = process.waitFor();
            if (exitCode != 0) {
                throw new RuntimeException("파이썬 실행 실패 (종료코드: " + exitCode + ")");
            }

            // ✨ 변경됨: 파일명 musinsa_data.json
            File file = new File("python/musinsa_data.json");
            if (!file.exists()) {
                throw new RuntimeException("크롤링 결과 파일(musinsa_data.json)이 없습니다.");
            }

            // 2. JSON 읽기
            ObjectMapper mapper = new ObjectMapper();
            List<MusinsaItemDTO> dtoList = mapper.readValue(file, new TypeReference<List<MusinsaItemDTO>>() {});

            // 3. DTO -> Entity 변환 (새로운 필드 포함)
            List<MusinsaItem> entityList = new ArrayList<>();

            for (MusinsaItemDTO dto : dtoList) {
                MusinsaItem entity = new MusinsaItem();

                // 기존 기본 정보
                entity.setRanking(dto.getRanking());
                entity.setBrand(dto.getBrand());
                entity.setTitle(dto.getTitle());
                entity.setPrice(dto.getPrice());
                entity.setImgUrl(dto.getImgUrl());
                entity.setSubImgUrl(dto.getSubImgUrl());

                // 🆕 추가된 정보 (카테고리, 좋아요, 별점, 후기)
                entity.setCategory(dto.getCategory());
                entity.setLikeCount(dto.getLikeCount());
                entity.setRating(dto.getRating());
                entity.setReviewCount(dto.getReviewCount());

                entityList.add(entity);
            }

            // 4. DB 저장
            musinsaRepository.deleteAll(); // 기존 데이터 삭제
            musinsaRepository.saveAll(entityList);

            System.out.println("✅ [무신사] DB 저장 완료: " + entityList.size() + "건");

        } catch (Exception e) {
            e.printStackTrace();
            throw new RuntimeException("크롤링 서비스 오류: " + e.getMessage());
        }
    }

    // 목록 조회용 메서드
    public List<MusinsaItem> getItems() {
        return musinsaRepository.findAll();
    }
}