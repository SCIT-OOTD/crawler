package net.datasa.crawling.musinsa.repository;

// 🔴 예전 경로: import net.datasa.crawling.entity.MusinsaItem;
// 🟢 바뀐 경로: musinsa 패키지 안에 있는 Entity를 가져와야 합니다.
import net.datasa.crawling.musinsa.entity.MusinsaItem;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MusinsaRepository extends JpaRepository<MusinsaItem, Long> {
}