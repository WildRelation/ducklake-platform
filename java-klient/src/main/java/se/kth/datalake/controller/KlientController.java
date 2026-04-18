package se.kth.datalake.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;
import se.kth.datalake.service.DatalakeService;

@Controller
public class KlientController {

    private final DatalakeService service;

    public KlientController(DatalakeService service) {
        this.service = service;
    }

    @GetMapping("/")
    public String index(Model model) {
        try {
            model.addAttribute("kunder", service.hamtaKunder());
        } catch (Exception e) {
            model.addAttribute("fel", "Kunde inte nå datalaken: " + e.getMessage());
        }
        return "index";
    }

    @PostMapping("/kunder")
    public String skapaKund(@RequestParam String namn,
                            @RequestParam String email,
                            @RequestParam(required = false) String telefon,
                            RedirectAttributes attrs) {
        try {
            service.skapaKund(namn, email, telefon);
            attrs.addFlashAttribute("success", "Kund skapad!");
        } catch (Exception e) {
            attrs.addFlashAttribute("fel", "Fel vid skapande: " + e.getMessage());
        }
        return "redirect:/";
    }

    @PostMapping("/kunder/{id}/radera")
    public String raderaKund(@PathVariable int id, RedirectAttributes attrs) {
        try {
            service.raderaKund(id);
            attrs.addFlashAttribute("success", "Kund raderad!");
        } catch (Exception e) {
            attrs.addFlashAttribute("fel", "Fel vid radering: " + e.getMessage());
        }
        return "redirect:/";
    }
}
