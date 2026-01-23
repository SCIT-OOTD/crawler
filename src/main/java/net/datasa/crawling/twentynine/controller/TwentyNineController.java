package net.datasa.crawling.twentynine.controller;

// ★ 중요: DTO 임포트를 지우고 Entity를 임포트하세요
// import net.datasa.crawling.twentynine.dto.TwentyNineDTO; (삭제)
import net.datasa.crawling.twentynine.entity.TwentyNineItem;
import net.datasa.crawling.twentynine.service.TwentyNineService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.List;

@Controller
@RequestMapping("/29cm")
public class TwentyNineController {

    @Autowired
    private TwentyNineService twentyNineService;

    @GetMapping("/crawl")
    public String crawl() {
        twentyNineService.runCrawling();
        return "redirect:/29cm/list";
    }

    @GetMapping("/list")
    public String list(Model model) {
        // ★ 여기를 수정하세요 (DTO -> Item)
        List<TwentyNineItem> productList = twentyNineService.getCrawledData();

        model.addAttribute("products", productList);
        model.addAttribute("count", productList.size());

        return "twentynine/list";
    }
}