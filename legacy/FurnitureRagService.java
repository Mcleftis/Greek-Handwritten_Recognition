package com.yourcompany.furniture.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Core RAG service for furniture sketch descriptions.
 *
 * RAG flow in this service:
 *   STORE  → text description ──[EmbeddingModel]──► float[] vector ──► pgvector table
 *   SEARCH → natural language query ──[EmbeddingModel]──► float[] ──► cosine similarity search ──► matching UUIDs
 *
 * The VectorStore bean (PgVectorStore) handles all embedding + SQL internally;
 * this service only deals with Spring AI's high-level Document / SearchRequest API.
 */
@Service
public class FurnitureRagService {

    private static final Logger log = LoggerFactory.getLogger(FurnitureRagService.class);

    // Key used to store/retrieve the sketch UUID inside Document metadata
    private static final String SKETCH_ID_KEY = "sketchId";

    // How many similar results to return from a similarity search
    private static final int TOP_K = 3;

    // Minimum cosine similarity score to consider a result relevant (0.0 – 1.0)
    // Tune this based on your data; 0.70 is a reasonable starting point
    private static final double SIMILARITY_THRESHOLD = 0.70;

    // Spring AI's VectorStore abstraction — backed by PgVectorStore at runtime
    private final VectorStore vectorStore;

    public FurnitureRagService(VectorStore vectorStore) {
        this.vectorStore = vectorStore;
    }

    // =========================================================================
    // STORE
    // =========================================================================

    /**
     * Converts a furniture sketch description into an embedding vector and
     * persists it in the pgvector table alongside the sketch's UUID as metadata.
     *
     * What happens internally:
     *   1. A Spring AI Document wraps the text + metadata.
     *   2. PgVectorStore calls the EmbeddingModel (OpenAI) → float[1536].
     *   3. The vector + metadata are inserted into `furniture_vector_store`.
     *
     * @param description  Free-text description, e.g. "Corner kitchen, MDF, 3 drawers"
     * @param sketchId     The UUID of the corresponding sketch entity in your DB
     */
    public void storeSketchDescription(String description, UUID sketchId) {
        // Metadata map — any key/value pairs you want to retrieve later
        // alongside the matching document (acts like a SELECT column in SQL)
        Map<String, Object> metadata = Map.of(SKETCH_ID_KEY, sketchId.toString());

        // Document is Spring AI's unit of content: text + optional metadata
        Document document = new Document(description, metadata);

        // add() triggers embedding + INSERT in a single call
        vectorStore.add(List.of(document));

        log.info("Stored embedding for sketchId={} | description='{}'",
                sketchId, description);
    }

    // =========================================================================
    // SEARCH
    // =========================================================================

    /**
     * Performs a semantic similarity search: finds the TOP_K sketch descriptions
     * that are closest (in vector space) to the user's natural language query.
     *
     * What happens internally:
     *   1. The query string is embedded via OpenAI → float[1536].
     *   2. PgVectorStore runs:
     *        SELECT ... FROM furniture_vector_store
     *        ORDER BY embedding <=> query_vector   -- <=> is cosine distance in pgvector
     *        LIMIT 3
     *   3. Results are filtered by SIMILARITY_THRESHOLD.
     *   4. We extract the sketchId from each document's metadata and return the list.
     *
     * @param userQuery  Natural language query, e.g. "white wardrobe with sliding doors"
     * @return           List of matching sketch UUIDs, ordered by similarity (best first)
     */
    public List<UUID> searchSimilarSketches(String userQuery) {
        log.info("Searching for: '{}'", userQuery);

        // SearchRequest builder — fluent API for controlling the similarity query
        SearchRequest request = SearchRequest
                .query(userQuery)           // the text to embed and search with
                .withTopK(TOP_K)            // max number of results to return
                .withSimilarityThreshold(SIMILARITY_THRESHOLD); // filter weak matches

        // similaritySearch returns List<Document> — each Document has the original
        // description text + whatever metadata we stored during storeSketchDescription()
        List<Document> results = vectorStore.similaritySearch(request);

        log.info("Found {} similar sketches for query='{}'", results.size(), userQuery);

        // Extract the sketchId from each result's metadata map and convert back to UUID
        return results.stream()
                .map(doc -> doc.getMetadata().get(SKETCH_ID_KEY))
                .filter(id -> id != null)
                .map(id -> UUID.fromString(id.toString()))
                .toList();
    }

    // =========================================================================
    // OPTIONAL: DELETE
    // =========================================================================

    /**
     * Removes a stored embedding by its Spring AI Document ID.
     * Call this when a sketch is deleted from your main database.
     *
     * Note: Spring AI's document ID is auto-generated at store time.
     * To support deletion by sketchId, you would need to store the
     * document ID alongside your sketch entity in PostgreSQL.
     *
     * @param documentId  The Spring AI document ID returned at store time
     */
    public void deleteSketchEmbedding(String documentId) {
        vectorStore.delete(List.of(documentId));
        log.info("Deleted embedding for documentId={}", documentId);
    }
}
