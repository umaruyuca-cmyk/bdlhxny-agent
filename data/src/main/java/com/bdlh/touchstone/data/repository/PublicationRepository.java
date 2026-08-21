package com.bdlh.touchstone.data.repository;

import static com.bdlh.touchstone.data.domain.RunPayloads.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

/** 发布登记(publications / publication_runs):公开静态产物与内部批次的映射。 */
@Repository
public class PublicationRepository {
    private final JdbcTemplate jdbc;

    public PublicationRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public UUID registerPublication(RegisterPublicationRequest request) {
        UUID publicationId = UUID.randomUUID();
        Integer current = jdbc.queryForObject(
                "SELECT max(version) FROM touchstone.publications WHERE batch_id = ?",
                Integer.class,
                UUID.fromString(request.batchId()));
        int version = (current == null ? 0 : current) + 1;
        jdbc.update(
                """
                INSERT INTO touchstone.publications
                    (id, batch_id, version, title, status, field_policy_version,
                     index_storage_ref, content_hash, generated_at, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, now(), now())
                """,
                publicationId,
                UUID.fromString(request.batchId()),
                version,
                request.title(),
                request.status(),
                request.fieldPolicyVersion(),
                request.indexStorageRef(),
                request.contentHash());
        for (PublicationRunInput run : request.runs()) {
            jdbc.update(
                    """
                    INSERT INTO touchstone.publication_runs
                        (publication_id, run_id, public_storage_ref, public_content_hash)
                    VALUES (?, ?, ?, ?)
                    """,
                    publicationId,
                    UUID.fromString(run.runId()),
                    run.publicStorageRef(),
                    run.publicContentHash());
        }
        return publicationId;
    }

    public List<Map<String, Object>> listPublications(String batchId) {
        String filter = batchId == null ? "" : " WHERE batch_id = ?::uuid";
        Object[] args = batchId == null ? new Object[0] : new Object[] {batchId};
        return jdbc.queryForList(
                "SELECT id, batch_id, version, title, status, field_policy_version, "
                        + "index_storage_ref, content_hash, generated_at, published_at "
                        + "FROM touchstone.publications" + filter + " ORDER BY published_at DESC",
                args);
    }

    public Map<String, Object> getPublication(UUID publicationId) {
        Map<String, Object> publication = new LinkedHashMap<>(
                jdbc.queryForMap(
                        """
                        SELECT id, batch_id, version, title, status, field_policy_version,
                               index_storage_ref, content_hash, generated_at, published_at
                        FROM touchstone.publications WHERE id = ?
                        """,
                        publicationId));
        publication.put(
                "runs",
                jdbc.queryForList(
                        """
                        SELECT run_id, public_storage_ref, public_content_hash
                        FROM touchstone.publication_runs WHERE publication_id = ?
                        """,
                        publicationId));
        return publication;
    }
}
