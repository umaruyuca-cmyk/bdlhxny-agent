-- 20260822-tool-catalog-extended-fields.sql
-- GT-6：工具能力表扩展评测轴三列(副作用/需确认/风险级别)。
--
-- 设计取舍(见任务清单修订记录 2026-08-22(九)):
--   read_only 保持为治理轴(G2 只读红线)不动;side_effect 是评测轴新列,
--   供判官(GT-7)计算未确认写入率/查询误用写入率等指标。
--   不加 mock_only 列:评测目录整体即 mock,由所用 fixture set 表达。
--   金融 16 行不动:新列由 DEFAULT 覆盖(side_effect='none'/risk_level='low'),
--   不按私有读取语义回写 medium(需要时属所有者后续数据操作)。
-- 对现有数据:纯增列,默认值即时生效,无需回填。
-- 服务影响:执行前建议暂停 data 服务(列变更触发连接池语句缓存失效的风险低,
--   但 ALTER 与并发长查询可能短暂互等;lock_timeout 5s 兜底)。engine 无需重启
--   (loader 逐字段带默认读取,旧 payload 兼容)。
-- 回滚参考:ALTER TABLE touchstone.tool_capabilities
--   DROP COLUMN side_effect, DROP COLUMN requires_confirmation, DROP COLUMN risk_level;

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '1min';

ALTER TABLE touchstone.tool_capabilities
  ADD COLUMN side_effect VARCHAR(20) NOT NULL DEFAULT 'none'
    CONSTRAINT tool_capability_side_effect_valid CHECK (
        side_effect IN ('none', 'write', 'external_action')
    ),
  ADD COLUMN requires_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN risk_level VARCHAR(10) NOT NULL DEFAULT 'low'
    CONSTRAINT tool_capability_risk_valid CHECK (
        risk_level IN ('low', 'medium', 'high')
    );

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('20260822-tool-catalog-extended-fields.sql',
        'GT-6:tool_capabilities 增评测轴三列 side_effect/requires_confirmation/risk_level(默认 none/false/low,金融 16 行不动)')
ON CONFLICT DO NOTHING;

COMMIT;
