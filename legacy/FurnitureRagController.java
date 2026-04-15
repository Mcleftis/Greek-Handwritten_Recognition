package com.yourcompany.furniture.controller;

import com.yourcompany.furniture.service.FurnitureRagService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

/**
 * Thin REST layer that exposes the RAG service over HTTP.
 * Not strictly required — you can call FurnitureRagService directly
 * from any other service — but useful for manual testing with curl/Postman.
 */
@RestController
@RequestMapping("/api/rag/furniture")
public class FurnitureRagController {

    private final FurnitureRagService ragService;

    public FurnitureRagController(FurnitureRagService ragService) {
        this.ragService = ragService;
    }

    // ── STORE ─────────────────────────────────────────────────────────────────
    // POST /api/rag/furniture/store
    // Body: { "sketchId": "uuid-here", "description": "Corner kitchen, MDF, 3 drawers" }
    @PostMapping("/store")
    public ResponseEntity<String> store(@RequestBody StoreRequest request) {
        ragService.storeSketchDescription(request.description(), request.sketchId());
        return ResponseEntity.ok("Embedding stored for sketch " + request.sketchId());
    }

    // ── SEARCH ────────────────────────────────────────────────────────────────
    // GET /api/rag/furniture/search?query=white+wardrobe+with+sliding+doors
    @GetMapping("/search")
    public ResponseEntity<List<UUID>> search(@RequestParam String query) {
        List<UUID> results = ragService.searchSimilarSketches(query);
        return ResponseEntity.ok(results);
    }

    // Simple request record (Java 16+)
    public record StoreRequest(UUID sketchId, String description) {}
}
