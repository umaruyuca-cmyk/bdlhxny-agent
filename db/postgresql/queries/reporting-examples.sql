-- 按 Agent 实现计算一个批次中有效运行的 p50 和 p95 总时长。
SELECT r.agent_id,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY m.total_duration_ms) AS p50_ms,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY m.total_duration_ms) AS p95_ms
FROM touchstone.agent_runs r
JOIN touchstone.run_measurements m ON m.run_id = r.id
JOIN touchstone.evaluation_results e ON e.run_id = r.id
WHERE r.batch_id = :batch_id
  AND e.valid_run = true
GROUP BY r.agent_id;

-- 检查强制上下文是否被错误省略或只保留引用。
SELECT b.run_id, i.item_key, d.action, d.reason
FROM touchstone.context_builds b
JOIN touchstone.context_items i ON i.context_build_id = b.id
JOIN touchstone.context_decisions d
  ON d.context_build_id = b.id AND d.item_key = i.item_key
WHERE i.classification = 'required'
  AND d.action NOT IN ('kept', 'compressed', 'isolated');

-- 从一个公开运行工件追溯内部批次与运行。
SELECT p.batch_id,
       pr.run_id,
       pr.public_storage_ref,
       pr.public_content_hash
FROM touchstone.publications p
JOIN touchstone.publication_runs pr ON pr.publication_id = p.id
WHERE p.status = 'PUBLISHED'
  AND pr.run_id = :run_id;
