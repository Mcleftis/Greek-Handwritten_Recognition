package com.yourcompany.furniture.config;

import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.vectorstore.PgVectorStore;
import org.springframework.ai.vectorstore.PgVectorStore.PgDistanceType;
import org.springframework.ai.vectorstore.PgVectorStore.PgIndexType;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Registers the PgVectorStore as a Spring-managed bean.
 *
 * Spring AI's auto-configuration will handle this automatically when
 * spring-ai-pgvector-store-spring-boot-starter is on the classpath AND
 * all properties are set in application.yml.
 *
 * This explicit bean definition is provided so you can see exactly what
 * is being wired together and override any defaults easily.
 */
@Configuration
public class VectorStoreConfig {

    /**
     * PgVectorStore — the Spring AI abstraction over the pgvector PostgreSQL
     * extension.  It uses:
     *   - JdbcTemplate  : to run raw SQL (INSERT, SELECT with <-> operator)
     *   - EmbeddingModel: to convert text → float[] before storing/querying
     *
     * Both are auto-configured by Spring Boot; we just inject them here.
     */
    @Bean
    public PgVectorStore pgVectorStore(JdbcTemplate jdbcTemplate,
                                       EmbeddingModel embeddingModel) {
        return PgVectorStore.builder()
                // The JdbcTemplate connected to your PostgreSQL datasource
                .jdbcTemplate(jdbcTemplate)
                // The OpenAI embedding model defined in application.yml
                .embeddingModel(embeddingModel)
                // Table name — must match vectorstore.pgvector.table-name in yml
                .tableName("furniture_vector_store")
                // 1024 dims for text-embedding-3-small / mxbai-embed-large
                .dimensions(1024)
                // Cosine similarity is the standard metric for text embeddings
                .distanceType(PgDistanceType.COSINE_DISTANCE)
                // HNSW = Hierarchical Navigable Small World graph index
                // Fast approximate nearest-neighbour, ideal for production
                .indexType(PgIndexType.HNSW)
                // Creates the table + pgvector extension on startup if absent
                .initializeSchema(true)
                .build();
    }
}





