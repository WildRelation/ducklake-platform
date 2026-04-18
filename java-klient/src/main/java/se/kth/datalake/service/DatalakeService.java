package se.kth.datalake.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import se.kth.datalake.model.Kund;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Service
public class DatalakeService {

    @Value("${datalake.url}")
    private String datalakeUrl;

    @Value("${datalake.apikey}")
    private String apiKey;

    private final RestTemplate restTemplate = new RestTemplate();

    // ── GET ───────────────────────────────────────────────────────────────────

    public List<Kund> hamtaKunder() {
        Kund[] kunder = restTemplate.getForObject(
            datalakeUrl + "/api/kunder", Kund[].class
        );
        return kunder != null ? Arrays.asList(kunder) : List.of();
    }

    // ── POST ──────────────────────────────────────────────────────────────────

    public void skapaKund(String namn, String email, String telefon) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-API-Key", apiKey);

        Map<String, String> body = Map.of(
            "namn", namn,
            "email", email,
            "telefon", telefon != null ? telefon : ""
        );

        HttpEntity<Map<String, String>> request = new HttpEntity<>(body, headers);
        restTemplate.postForEntity(datalakeUrl + "/api/kunder", request, String.class);
    }

    // ── DELETE ────────────────────────────────────────────────────────────────

    public void raderaKund(int id) {
        HttpHeaders headers = new HttpHeaders();
        headers.set("X-API-Key", apiKey);

        HttpEntity<Void> request = new HttpEntity<>(headers);
        restTemplate.exchange(
            datalakeUrl + "/api/kunder/" + id,
            HttpMethod.DELETE,
            request,
            String.class
        );
    }
}
