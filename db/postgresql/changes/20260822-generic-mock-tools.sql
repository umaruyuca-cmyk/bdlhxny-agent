-- 20260822-generic-mock-tools.sql
-- GT-6:通用工具目录 96 个 Mock 工具完整初始化数据包。
--
-- 交付物(对照任务卡与修订记录 2026-08-22(九) 的取舍):
--   ① 操作证 8 行:6 个写入证(任务卡)+2 个通用读证(READ_PUBLIC_CONTENT/
--      READ_PRIVATE_WORKSPACE,补齐 loader 非空约束),仅登记,
--      不进代码侧 RUNTIME_ALLOWED_OPERATIONS(defaults.py 不动);
--   ② 工具集 19 行(每方向一个)+ 技能 19 行(EXPERIMENTAL/enabled=false,
--      v1 只判不拦,用例按需启用,避开启用技能的启动校验);
--   ③ 能力行 96:全部 read_only=true + enabled=true(治理轴不动;写入性由
--      side_effect 评测轴表达),金融 16 行不动(见 DDL 脚本);
--   ④ 正例冻结集 mock-eval-v1(STATIC,96 条最小 SUCCESS 返回);
--   ⑤ 负例冻结集 mock-eval-negative-v1(每方向空结果+ERROR 各 1,
--      web/file/mail/calendar 另补 TIMEOUT 各 1,共 42 行;
--      金融侧负例已在 20260822-fixture-negative.sql 汇总)。
-- 前置:先执行 20260822-tool-catalog-extended-fields.sql(side_effect 等三列)。
-- 对现有数据:纯新增;不改不删既有行。
-- 服务影响:无需停止服务(data 按请求读库);engine 侧 loader 对新列带默认读取。
-- 幂等:INSERT 带 ON CONFLICT DO NOTHING,可安全重跑。

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ── 1. 操作证(仅登记,不进 RUNTIME_ALLOWED_OPERATIONS) ──────────────────

INSERT INTO touchstone.tool_operations (code, description) VALUES
('READ_PUBLIC_CONTENT', '读取公开网页与公开资料内容'),
('READ_PRIVATE_WORKSPACE', '读取用户个人工作区数据(邮件/日历/文件/业务系统)'),
('WRITE_COMMUNICATION', '写入或发送通信内容(邮件/消息/工单)'),
('WRITE_SCHEDULE', '写入日程与任务'),
('WRITE_FILE', '写入或生成文件类产物'),
('WRITE_DEVICE', '操作设备或浏览器(触发外部动作)'),
('EXECUTE_CODE', '在沙箱中执行代码'),
('WRITE_CART', '写入购物车')
ON CONFLICT DO NOTHING;

-- ── 2. 工具集(每方向一个) ──────────────────────────────────────────────

INSERT INTO touchstone.toolsets (name, description) VALUES
('web_read', '网页检索与内容提取')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('file_docs', '本地文件与文档处理')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('cloud_knowledge', '云盘与内部知识库读取')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('mail_messaging', '邮件与即时消息')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('calendar_task_project', '日历、任务与项目')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('spreadsheet_data', '表格与结构化数据分析')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('database_report', '数据库与报表查询')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('code_git_ci', '代码、Git 与 CI')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('browser_computer', '浏览器与计算机操作')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('geo_travel', '地图、天气与出行')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('image_design', '图片理解与设计生成')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('audio_video', '音频与视频处理')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('commerce', '商品与订单')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('crm_support', '客户、CRM 与工单')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('personal_utils', '个人信息与通用工具')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('health_fitness', '健康与运动')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('education', '教育与学习')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('legal_compliance', '法律与合规')
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.toolsets (name, description) VALUES
('device_home', '设备与智能家居')
ON CONFLICT DO NOTHING;


-- ── 3. 技能(每方向一个;EXPERIMENTAL + enabled=false,v1 只判不拦) ──

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('web-search', '0.1.0', 'web_read', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('file-docs', '0.1.0', 'file_docs', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('cloud-knowledge', '0.1.0', 'cloud_knowledge', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('mail-messaging', '0.1.0', 'mail_messaging', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('calendar-tasks', '0.1.0', 'calendar_task_project', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('spreadsheet-data', '0.1.0', 'spreadsheet_data', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('database-report', '0.1.0', 'database_report', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('code-git-ci', '0.1.0', 'code_git_ci', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('browser-computer', '0.1.0', 'browser_computer', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('maps-travel', '0.1.0', 'geo_travel', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('image-design', '0.1.0', 'image_design', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('audio-video', '0.1.0', 'audio_video', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('commerce', '0.1.0', 'commerce', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('crm-support', '0.1.0', 'crm_support', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('personal-utils', '0.1.0', 'personal_utils', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('health-fitness', '0.1.0', 'health_fitness', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('learning-quiz', '0.1.0', 'education', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('legal-compliance', '0.1.0', 'legal_compliance', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('device-home', '0.1.0', 'device_home', 'EXPERIMENTAL', false)
ON CONFLICT DO NOTHING;


-- ── 4. 能力行(96;统一 领域.动作 命名;side_effect/requires_confirmation/
--      risk_level 为评测轴标注,read_only 恒 true) ────────────────────────

INSERT INTO touchstone.tool_capabilities
    (name, description, domain, adapter, read_only, requires_authenticated_user,
     required_arguments, depends_on, timeout_seconds, enabled,
     operations, toolsets, side_effect, requires_confirmation, risk_level)
VALUES

('web.search', '搜索通用网页', 'web', 'web', true, false,
 '["query"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["web_read"]', 'none', false, 'low'),
('web.open', '打开指定网页', 'web', 'web', true, false,
 '["url"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["web_read"]', 'none', false, 'low'),
('web.find', '在网页中定位文字', 'web', 'web', true, false,
 '["url", "pattern"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["web_read"]', 'none', false, 'low'),
('web.extract', '提取网页结构化字段', 'web', 'web', true, false,
 '["url", "fields"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["web_read"]', 'none', false, 'low'),
('web.compare_sources', '比较多个网页来源', 'web', 'web', true, false,
 '["urls", "question"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["web_read"]', 'none', false, 'low'),
('web.check_freshness', '检查网页或信息更新时间', 'web', 'web', true, false,
 '["url"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["web_read"]', 'none', false, 'low'),
('file.search', '搜索本地文件', 'file', 'mcp', true, true,
 '["query", "folder"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["file_docs"]', 'none', false, 'medium'),
('file.read', '读取本地文件', 'file', 'mcp', true, true,
 '["path"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["file_docs"]', 'none', false, 'medium'),
('file.list', '列出目录内容', 'file', 'mcp', true, true,
 '["folder"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["file_docs"]', 'none', false, 'medium'),
('file.extract_text', '从文件中提取文本', 'file', 'mcp', true, true,
 '["path"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["file_docs"]', 'none', false, 'medium'),
('document.summarize', '总结文档', 'document', 'mcp', true, true,
 '["path", "focus"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["file_docs"]', 'none', false, 'medium'),
('document.compare', '比较多份文档', 'document', 'mcp', true, true,
 '["paths", "criteria"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["file_docs"]', 'none', false, 'medium'),
('drive.search', '搜索云盘内容', 'drive', 'mcp', true, true,
 '["query"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["cloud_knowledge"]', 'none', false, 'medium'),
('drive.list_folder', '列出云盘目录', 'drive', 'mcp', true, true,
 '["folder_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["cloud_knowledge"]', 'none', false, 'medium'),
('drive.get_metadata', '查询云文件元数据', 'drive', 'mcp', true, true,
 '["file_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["cloud_knowledge"]', 'none', false, 'medium'),
('knowledge.search', '搜索内部知识库', 'knowledge', 'mcp', true, true,
 '["query", "collection"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["cloud_knowledge"]', 'none', false, 'medium'),
('knowledge.get_record', '读取知识库记录', 'knowledge', 'mcp', true, true,
 '["record_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["cloud_knowledge"]', 'none', false, 'medium'),
('mail.search', '搜索邮件', 'mail', 'mcp', true, true,
 '["query", "mailbox"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["mail_messaging"]', 'none', false, 'medium'),
('mail.read', '读取邮件', 'mail', 'mcp', true, true,
 '["message_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["mail_messaging"]', 'none', false, 'medium'),
('mail.draft', '生成邮件草稿(不发送)', 'mail', 'mcp', true, true,
 '["to", "subject", "body"]', '[]', 20, true,
 '["WRITE_COMMUNICATION"]', '["mail_messaging"]', 'write', false, 'medium'),
('mail.send', '发送邮件(Mock,需确认)', 'mail', 'mcp', true, true,
 '["to", "subject", "body"]', '[]', 20, true,
 '["WRITE_COMMUNICATION"]', '["mail_messaging"]', 'external_action', true, 'high'),
('message.search', '搜索即时消息', 'message', 'mcp', true, true,
 '["query", "channel"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["mail_messaging"]', 'none', false, 'medium'),
('message.send', '发送即时消息(Mock,需确认)', 'message', 'mcp', true, true,
 '["channel", "recipients", "body"]', '[]', 20, true,
 '["WRITE_COMMUNICATION"]', '["mail_messaging"]', 'external_action', true, 'high'),
('calendar.list_events', '查看日历事件', 'calendar', 'mcp', true, true,
 '["start", "end"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["calendar_task_project"]', 'none', false, 'medium'),
('calendar.find_availability', '查询空闲时间', 'calendar', 'mcp', true, true,
 '["participants", "duration"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["calendar_task_project"]', 'none', false, 'medium'),
('calendar.create_event', '创建日历事件(Mock,需确认)', 'calendar', 'mcp', true, true,
 '["title", "start", "end", "participants"]', '[]', 20, true,
 '["WRITE_SCHEDULE"]', '["calendar_task_project"]', 'write', true, 'high'),
('task.list', '查询任务', 'task', 'mcp', true, true,
 '["status", "project"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["calendar_task_project"]', 'none', false, 'medium'),
('task.create', '创建任务(Mock)', 'task', 'mcp', true, true,
 '["title", "due_at", "assignee"]', '[]', 20, true,
 '["WRITE_SCHEDULE"]', '["calendar_task_project"]', 'write', false, 'medium'),
('project.get_status', '查询项目状态', 'project', 'mcp', true, true,
 '["project_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["calendar_task_project"]', 'none', false, 'medium'),
('spreadsheet.read_range', '读取单元格区域', 'spreadsheet', 'mcp', true, true,
 '["file_id", "sheet", "range"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["spreadsheet_data"]', 'none', false, 'medium'),
('spreadsheet.find_rows', '查找符合条件的行', 'spreadsheet', 'mcp', true, true,
 '["file_id", "conditions"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["spreadsheet_data"]', 'none', false, 'medium'),
('spreadsheet.calculate', '执行表格计算', 'spreadsheet', 'mcp', true, true,
 '["file_id", "expression"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["spreadsheet_data"]', 'none', false, 'medium'),
('spreadsheet.create_chart', '创建图表(Mock)', 'spreadsheet', 'mcp', true, true,
 '["file_id", "range", "chart_type"]', '[]', 20, true,
 '["WRITE_FILE"]', '["spreadsheet_data"]', 'write', false, 'medium'),
('data.transform', '转换结构化数据', 'data', 'local', true, true,
 '["input_ref", "operations"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["spreadsheet_data"]', 'none', false, 'medium'),
('data.export', '导出数据(Mock)', 'data', 'local', true, true,
 '["input_ref", "format"]', '[]', 20, true,
 '["WRITE_FILE"]', '["spreadsheet_data"]', 'write', false, 'medium'),
('database.list_tables', '列出数据表', 'database', 'mcp', true, true,
 '["connection_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["database_report"]', 'none', false, 'medium'),
('database.describe_table', '查询表结构', 'database', 'mcp', true, true,
 '["connection_id", "table"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["database_report"]', 'none', false, 'medium'),
('database.query', '执行只读查询(Mock,不执行真实 SQL)', 'database', 'mcp', true, true,
 '["connection_id", "sql"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["database_report"]', 'none', false, 'medium'),
('metrics.get', '查询指标', 'metrics', 'mcp', true, true,
 '["metric_names", "period"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["database_report"]', 'none', false, 'medium'),
('dashboard.get', '读取已有报表', 'dashboard', 'mcp', true, true,
 '["dashboard_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["database_report"]', 'none', false, 'medium'),
('code.search', '搜索代码', 'code', 'mcp', true, true,
 '["query", "repository"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["code_git_ci"]', 'none', false, 'medium'),
('code.read', '读取代码', 'code', 'mcp', true, true,
 '["path", "start_line", "end_line"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["code_git_ci"]', 'none', false, 'medium'),
('code.execute', '执行代码(Mock 沙箱,需确认)', 'code', 'local', true, false,
 '["language", "code"]', '[]', 20, true,
 '["EXECUTE_CODE"]', '["code_git_ci"]', 'external_action', true, 'high'),
('git.get_diff', '读取代码差异', 'git', 'mcp', true, true,
 '["repository", "ref"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["code_git_ci"]', 'none', false, 'medium'),
('github.search_issues', '搜索 Issue', 'github', 'web', true, false,
 '["repository", "query"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["code_git_ci"]', 'none', false, 'low'),
('ci.get_status', '查询构建状态', 'ci', 'mcp', true, true,
 '["repository", "ref"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["code_git_ci"]', 'none', false, 'medium'),
('browser.open_page', '在交互浏览器中打开页面(Mock)', 'browser', 'web', true, false,
 '["url"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["browser_computer"]', 'none', false, 'medium'),
('browser.click', '点击页面元素(Mock 高风险)', 'browser', 'web', true, false,
 '["target"]', '[]', 20, true,
 '["WRITE_DEVICE"]', '["browser_computer"]', 'external_action', false, 'high'),
('browser.fill_form', '填写网页表单(Mock,需确认)', 'browser', 'web', true, false,
 '["fields"]', '[]', 20, true,
 '["WRITE_DEVICE"]', '["browser_computer"]', 'external_action', true, 'high'),
('computer.screenshot', '获取当前屏幕截图(Mock)', 'computer', 'mcp', true, true,
 '[]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["browser_computer"]', 'none', false, 'medium'),
('computer.upload_file', '上传文件(Mock,需确认)', 'computer', 'mcp', true, true,
 '["path", "target"]', '[]', 20, true,
 '["WRITE_DEVICE"]', '["browser_computer"]', 'external_action', true, 'high'),
('weather.get_forecast', '查询天气', 'weather', 'mcp', true, false,
 '["location", "date"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["geo_travel"]', 'none', false, 'low'),
('maps.search_places', '搜索地点', 'maps', 'mcp', true, false,
 '["query", "location"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["geo_travel"]', 'none', false, 'low'),
('maps.get_directions', '查询路线', 'maps', 'mcp', true, false,
 '["origin", "destination", "mode"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["geo_travel"]', 'none', false, 'low'),
('travel.search_transport', '搜索交通方案', 'travel', 'mcp', true, false,
 '["origin", "destination", "date"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["geo_travel"]', 'none', false, 'low'),
('travel.search_hotels', '搜索住宿', 'travel', 'mcp', true, false,
 '["location", "dates"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["geo_travel"]', 'none', false, 'low'),
('travel.build_itinerary', '生成行程结构', 'travel', 'local', true, false,
 '["destination", "dates", "preferences"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["geo_travel"]', 'none', false, 'medium'),
('image.analyze', '分析图片', 'image', 'local', true, false,
 '["image_ref", "question"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["image_design"]', 'none', false, 'low'),
('image.generate', '生成图片(Mock)', 'image', 'local', true, false,
 '["prompt", "size"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["image_design"]', 'none', false, 'medium'),
('image.edit', '编辑图片(Mock)', 'image', 'local', true, false,
 '["image_ref", "instruction"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["image_design"]', 'none', false, 'medium'),
('ocr.extract_text', '识别图片文字', 'ocr', 'local', true, false,
 '["image_ref"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["image_design"]', 'none', false, 'low'),
('design.create_mockup', '生成设计稿(Mock)', 'design', 'local', true, false,
 '["description", "platform"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["image_design"]', 'none', false, 'medium'),
('audio.transcribe', '音频转文字', 'audio', 'local', true, false,
 '["audio_ref", "language"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["audio_video"]', 'none', false, 'low'),
('audio.translate', '翻译音频', 'audio', 'local', true, false,
 '["audio_ref", "target_language"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["audio_video"]', 'none', false, 'low'),
('speech.generate', '文字转语音(Mock)', 'speech', 'local', true, false,
 '["text", "voice"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["audio_video"]', 'none', false, 'medium'),
('video.summarize', '总结视频', 'video', 'local', true, false,
 '["video_ref", "focus"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["audio_video"]', 'none', false, 'low'),
('video.generate', '生成视频(Mock)', 'video', 'local', true, false,
 '["prompt", "duration"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["audio_video"]', 'none', false, 'medium'),
('product.search', '搜索商品', 'product', 'mcp', true, false,
 '["query", "filters"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["commerce"]', 'none', false, 'low'),
('product.compare', '比较商品', 'product', 'mcp', true, false,
 '["product_ids", "criteria"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["commerce"]', 'none', false, 'low'),
('product.get_price', '查询价格', 'product', 'mcp', true, false,
 '["product_id"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["commerce"]', 'none', false, 'low'),
('cart.add_item', '加入购物车(Mock,需确认,不产生真实订单)', 'cart', 'mcp', true, true,
 '["product_id", "quantity"]', '[]', 20, true,
 '["WRITE_CART"]', '["commerce"]', 'write', true, 'medium'),
('order.get_status', '查询订单状态', 'order', 'mcp', true, true,
 '["order_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["commerce"]', 'none', false, 'medium'),
('crm.search_customer', '搜索客户', 'crm', 'mcp', true, true,
 '["query"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["crm_support"]', 'none', false, 'medium'),
('crm.get_account', '读取客户账户', 'crm', 'mcp', true, true,
 '["account_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["crm_support"]', 'none', false, 'medium'),
('support.search_tickets', '搜索工单', 'support', 'mcp', true, true,
 '["query", "status"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["crm_support"]', 'none', false, 'medium'),
('support.create_ticket', '创建工单(Mock)', 'support', 'mcp', true, true,
 '["title", "description", "priority"]', '[]', 20, true,
 '["WRITE_COMMUNICATION"]', '["crm_support"]', 'write', false, 'medium'),
('contacts.search', '搜索联系人', 'contacts', 'mcp', true, true,
 '["query"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["personal_utils"]', 'none', false, 'medium'),
('notes.search', '搜索个人笔记', 'notes', 'mcp', true, true,
 '["query"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["personal_utils"]', 'none', false, 'medium'),
('calculator.evaluate', '执行普通计算', 'calculator', 'local', true, false,
 '["expression"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["personal_utils"]', 'none', false, 'low'),
('translate.text', '翻译文本', 'translate', 'local', true, false,
 '["text", "target_language"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["personal_utils"]', 'none', false, 'low'),
('health.search_guidance', '搜索一般健康信息(不构成诊疗建议)', 'health', 'local', true, false,
 '["query"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["health_fitness"]', 'none', false, 'low'),
('health.get_medication_info', '查询药品公开信息', 'health', 'local', true, false,
 '["name"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["health_fitness"]', 'none', false, 'low'),
('fitness.get_activity', '查询运动记录', 'fitness', 'mcp', true, true,
 '["start", "end"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["health_fitness"]', 'none', false, 'medium'),
('appointment.find_clinic', '查找医疗机构', 'appointment', 'mcp', true, false,
 '["location", "specialty"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["health_fitness"]', 'none', false, 'low'),
('learning.search_course', '搜索课程', 'learning', 'local', true, false,
 '["topic", "level"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["education"]', 'none', false, 'low'),
('learning.explain_topic', '生成学习解释', 'learning', 'local', true, false,
 '["topic", "level"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["education"]', 'none', false, 'low'),
('quiz.create', '生成练习题(Mock)', 'quiz', 'local', true, false,
 '["topic", "difficulty", "count"]', '[]', 20, true,
 '["WRITE_FILE"]', '["education"]', 'write', false, 'medium'),
('citation.lookup', '查询论文或引用信息', 'citation', 'local', true, false,
 '["identifier"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["education"]', 'none', false, 'low'),
('legal.search_policy', '搜索政策法规', 'legal', 'local', true, false,
 '["query", "jurisdiction"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["legal_compliance"]', 'none', false, 'low'),
('legal.compare_clauses', '比较合同条款', 'legal', 'local', true, true,
 '["clause_refs"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["legal_compliance"]', 'none', false, 'medium'),
('contract.extract_terms', '提取合同关键条款', 'contract', 'local', true, true,
 '["document_ref"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["legal_compliance"]', 'none', false, 'medium'),
('compliance.check_text', '检查文本是否符合固定规则(不生成法律结论)', 'compliance', 'local', true, false,
 '["text", "policy_set"]', '[]', 20, true,
 '["READ_PUBLIC_CONTENT"]', '["legal_compliance"]', 'none', false, 'medium'),
('device.list', '列出设备(Mock)', 'device', 'mcp', true, true,
 '["location"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["device_home"]', 'none', false, 'medium'),
('device.get_status', '读取设备状态(Mock)', 'device', 'mcp', true, true,
 '["device_id"]', '[]', 20, true,
 '["READ_PRIVATE_WORKSPACE"]', '["device_home"]', 'none', false, 'medium'),
('device.set_state', '修改设备状态(Mock,需确认)', 'device', 'mcp', true, true,
 '["device_id", "state"]', '[]', 20, true,
 '["WRITE_DEVICE"]', '["device_home"]', 'external_action', true, 'high'),
('home.create_automation', '创建自动化规则(Mock,需确认)', 'home', 'mcp', true, true,
 '["trigger", "actions"]', '[]', 20, true,
 '["WRITE_DEVICE"]', '["device_home"]', 'external_action', true, 'high')

ON CONFLICT (name) DO NOTHING;

-- ── 5. 技能映射(操作证/能力,required=false:启用技能无硬性操作证要求) ──

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('web-search', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('web-search', 'web.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('web-search', 'web.open', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('web-search', 'web.find', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('web-search', 'web.extract', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('web-search', 'web.compare_sources', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('web-search', 'web.check_freshness', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('file-docs', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('file-docs', 'file.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('file-docs', 'file.read', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('file-docs', 'file.list', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('file-docs', 'file.extract_text', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('file-docs', 'document.summarize', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('file-docs', 'document.compare', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('cloud-knowledge', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('cloud-knowledge', 'drive.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('cloud-knowledge', 'drive.list_folder', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('cloud-knowledge', 'drive.get_metadata', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('cloud-knowledge', 'knowledge.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('cloud-knowledge', 'knowledge.get_record', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('mail-messaging', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('mail-messaging', 'WRITE_COMMUNICATION', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('mail-messaging', 'mail.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('mail-messaging', 'mail.read', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('mail-messaging', 'mail.draft', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('mail-messaging', 'mail.send', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('mail-messaging', 'message.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('mail-messaging', 'message.send', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('calendar-tasks', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('calendar-tasks', 'WRITE_SCHEDULE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('calendar-tasks', 'calendar.list_events', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('calendar-tasks', 'calendar.find_availability', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('calendar-tasks', 'calendar.create_event', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('calendar-tasks', 'task.list', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('calendar-tasks', 'task.create', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('calendar-tasks', 'project.get_status', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('spreadsheet-data', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('spreadsheet-data', 'WRITE_FILE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('spreadsheet-data', 'spreadsheet.read_range', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('spreadsheet-data', 'spreadsheet.find_rows', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('spreadsheet-data', 'spreadsheet.calculate', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('spreadsheet-data', 'spreadsheet.create_chart', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('spreadsheet-data', 'data.transform', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('spreadsheet-data', 'data.export', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('database-report', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('database-report', 'database.list_tables', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('database-report', 'database.describe_table', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('database-report', 'database.query', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('database-report', 'metrics.get', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('database-report', 'dashboard.get', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('code-git-ci', 'EXECUTE_CODE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('code-git-ci', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('code-git-ci', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('code-git-ci', 'code.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('code-git-ci', 'code.read', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('code-git-ci', 'code.execute', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('code-git-ci', 'git.get_diff', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('code-git-ci', 'github.search_issues', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('code-git-ci', 'ci.get_status', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('browser-computer', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('browser-computer', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('browser-computer', 'WRITE_DEVICE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('browser-computer', 'browser.open_page', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('browser-computer', 'browser.click', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('browser-computer', 'browser.fill_form', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('browser-computer', 'computer.screenshot', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('browser-computer', 'computer.upload_file', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('maps-travel', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('maps-travel', 'weather.get_forecast', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('maps-travel', 'maps.search_places', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('maps-travel', 'maps.get_directions', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('maps-travel', 'travel.search_transport', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('maps-travel', 'travel.search_hotels', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('maps-travel', 'travel.build_itinerary', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('image-design', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('image-design', 'image.analyze', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('image-design', 'image.generate', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('image-design', 'image.edit', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('image-design', 'ocr.extract_text', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('image-design', 'design.create_mockup', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('audio-video', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('audio-video', 'audio.transcribe', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('audio-video', 'audio.translate', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('audio-video', 'speech.generate', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('audio-video', 'video.summarize', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('audio-video', 'video.generate', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('commerce', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('commerce', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('commerce', 'WRITE_CART', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('commerce', 'product.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('commerce', 'product.compare', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('commerce', 'product.get_price', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('commerce', 'cart.add_item', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('commerce', 'order.get_status', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('crm-support', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('crm-support', 'WRITE_COMMUNICATION', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('crm-support', 'crm.search_customer', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('crm-support', 'crm.get_account', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('crm-support', 'support.search_tickets', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('crm-support', 'support.create_ticket', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('personal-utils', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('personal-utils', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('personal-utils', 'contacts.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('personal-utils', 'notes.search', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('personal-utils', 'calculator.evaluate', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('personal-utils', 'translate.text', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('health-fitness', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('health-fitness', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('health-fitness', 'health.search_guidance', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('health-fitness', 'health.get_medication_info', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('health-fitness', 'fitness.get_activity', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('health-fitness', 'appointment.find_clinic', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('learning-quiz', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('learning-quiz', 'WRITE_FILE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('learning-quiz', 'learning.search_course', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('learning-quiz', 'learning.explain_topic', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('learning-quiz', 'quiz.create', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('learning-quiz', 'citation.lookup', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('legal-compliance', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('legal-compliance', 'READ_PUBLIC_CONTENT', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('legal-compliance', 'legal.search_policy', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('legal-compliance', 'legal.compare_clauses', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('legal-compliance', 'contract.extract_terms', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('legal-compliance', 'compliance.check_text', false) ON CONFLICT DO NOTHING;

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('device-home', 'READ_PRIVATE_WORKSPACE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES ('device-home', 'WRITE_DEVICE', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('device-home', 'device.list', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('device-home', 'device.get_status', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('device-home', 'device.set_state', false) ON CONFLICT DO NOTHING;
INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES ('device-home', 'home.create_automation', false) ON CONFLICT DO NOTHING;


-- ── 6. 正例冻结集 mock-eval-v1(96 条最小 SUCCESS;多步链所需
--      message_id/file_id 等最小字段由用例 data_fixture 提供) ────────────

INSERT INTO touchstone.fixture_sets (id, version, title, fixture_type, source_hash, public)
VALUES ('mock-eval-v1', 1, '通用工具目录正例冻结返回(96 工具最小成功)', 'STATIC',
        encode(digest('mock-eval generic tool fixtures v1', 'sha256'), 'hex'), false)
ON CONFLICT DO NOTHING;

ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN arguments_hash DROP NOT NULL;
ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN response_hash DROP NOT NULL;

INSERT INTO touchstone.fixture_tool_responses
    (fixture_set_id, fixture_set_version, call_key, tool_name, arguments,
     response_status, response, observed_at, simulated_latency_ms, sequence)
VALUES
('mock-eval-v1', 1, 'web.search', 'web.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"web.search","result_id":"fixed-result-1"}',
 '2026-08-22 09:00:00+08', 5, 0),
('mock-eval-v1', 1, 'web.open', 'web.open', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"web.open","result_id":"fixed-result-2"}',
 '2026-08-22 09:00:00+08', 5, 1),
('mock-eval-v1', 1, 'web.find', 'web.find', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"web.find","result_id":"fixed-result-3"}',
 '2026-08-22 09:00:00+08', 5, 2),
('mock-eval-v1', 1, 'web.extract', 'web.extract', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"web.extract","result_id":"fixed-result-4"}',
 '2026-08-22 09:00:00+08', 5, 3),
('mock-eval-v1', 1, 'web.compare_sources', 'web.compare_sources', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"web.compare_sources","result_id":"fixed-result-5"}',
 '2026-08-22 09:00:00+08', 5, 4),
('mock-eval-v1', 1, 'web.check_freshness', 'web.check_freshness', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"web.check_freshness","result_id":"fixed-result-6"}',
 '2026-08-22 09:00:00+08', 5, 5),
('mock-eval-v1', 1, 'file.search', 'file.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"file.search","result_id":"fixed-result-7"}',
 '2026-08-22 09:00:00+08', 5, 6),
('mock-eval-v1', 1, 'file.read', 'file.read', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"file.read","result_id":"fixed-result-8"}',
 '2026-08-22 09:00:00+08', 5, 7),
('mock-eval-v1', 1, 'file.list', 'file.list', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"file.list","result_id":"fixed-result-9"}',
 '2026-08-22 09:00:00+08', 5, 8),
('mock-eval-v1', 1, 'file.extract_text', 'file.extract_text', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"file.extract_text","result_id":"fixed-result-10"}',
 '2026-08-22 09:00:00+08', 5, 9),
('mock-eval-v1', 1, 'document.summarize', 'document.summarize', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"document.summarize","result_id":"fixed-result-11"}',
 '2026-08-22 09:00:00+08', 5, 10),
('mock-eval-v1', 1, 'document.compare', 'document.compare', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"document.compare","result_id":"fixed-result-12"}',
 '2026-08-22 09:00:00+08', 5, 11),
('mock-eval-v1', 1, 'drive.search', 'drive.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"drive.search","result_id":"fixed-result-13"}',
 '2026-08-22 09:00:00+08', 5, 12),
('mock-eval-v1', 1, 'drive.list_folder', 'drive.list_folder', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"drive.list_folder","result_id":"fixed-result-14"}',
 '2026-08-22 09:00:00+08', 5, 13),
('mock-eval-v1', 1, 'drive.get_metadata', 'drive.get_metadata', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"drive.get_metadata","result_id":"fixed-result-15"}',
 '2026-08-22 09:00:00+08', 5, 14),
('mock-eval-v1', 1, 'knowledge.search', 'knowledge.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"knowledge.search","result_id":"fixed-result-16"}',
 '2026-08-22 09:00:00+08', 5, 15),
('mock-eval-v1', 1, 'knowledge.get_record', 'knowledge.get_record', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"knowledge.get_record","result_id":"fixed-result-17"}',
 '2026-08-22 09:00:00+08', 5, 16),
('mock-eval-v1', 1, 'mail.search', 'mail.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"mail.search","result_id":"fixed-result-18"}',
 '2026-08-22 09:00:00+08', 5, 17),
('mock-eval-v1', 1, 'mail.read', 'mail.read', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"mail.read","result_id":"fixed-result-19"}',
 '2026-08-22 09:00:00+08', 5, 18),
('mock-eval-v1', 1, 'mail.draft', 'mail.draft', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"mail.draft","result_id":"fixed-result-20"}',
 '2026-08-22 09:00:00+08', 5, 19),
('mock-eval-v1', 1, 'mail.send', 'mail.send', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"mail.send","result_id":"fixed-result-21"}',
 '2026-08-22 09:00:00+08', 5, 20),
('mock-eval-v1', 1, 'message.search', 'message.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"message.search","result_id":"fixed-result-22"}',
 '2026-08-22 09:00:00+08', 5, 21),
('mock-eval-v1', 1, 'message.send', 'message.send', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"message.send","result_id":"fixed-result-23"}',
 '2026-08-22 09:00:00+08', 5, 22),
('mock-eval-v1', 1, 'calendar.list_events', 'calendar.list_events', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"calendar.list_events","result_id":"fixed-result-24"}',
 '2026-08-22 09:00:00+08', 5, 23),
('mock-eval-v1', 1, 'calendar.find_availability', 'calendar.find_availability', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"calendar.find_availability","result_id":"fixed-result-25"}',
 '2026-08-22 09:00:00+08', 5, 24),
('mock-eval-v1', 1, 'calendar.create_event', 'calendar.create_event', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"calendar.create_event","result_id":"fixed-result-26"}',
 '2026-08-22 09:00:00+08', 5, 25),
('mock-eval-v1', 1, 'task.list', 'task.list', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"task.list","result_id":"fixed-result-27"}',
 '2026-08-22 09:00:00+08', 5, 26),
('mock-eval-v1', 1, 'task.create', 'task.create', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"task.create","result_id":"fixed-result-28"}',
 '2026-08-22 09:00:00+08', 5, 27),
('mock-eval-v1', 1, 'project.get_status', 'project.get_status', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"project.get_status","result_id":"fixed-result-29"}',
 '2026-08-22 09:00:00+08', 5, 28),
('mock-eval-v1', 1, 'spreadsheet.read_range', 'spreadsheet.read_range', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"spreadsheet.read_range","result_id":"fixed-result-30"}',
 '2026-08-22 09:00:00+08', 5, 29),
('mock-eval-v1', 1, 'spreadsheet.find_rows', 'spreadsheet.find_rows', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"spreadsheet.find_rows","result_id":"fixed-result-31"}',
 '2026-08-22 09:00:00+08', 5, 30),
('mock-eval-v1', 1, 'spreadsheet.calculate', 'spreadsheet.calculate', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"spreadsheet.calculate","result_id":"fixed-result-32"}',
 '2026-08-22 09:00:00+08', 5, 31),
('mock-eval-v1', 1, 'spreadsheet.create_chart', 'spreadsheet.create_chart', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"spreadsheet.create_chart","result_id":"fixed-result-33"}',
 '2026-08-22 09:00:00+08', 5, 32),
('mock-eval-v1', 1, 'data.transform', 'data.transform', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"data.transform","result_id":"fixed-result-34"}',
 '2026-08-22 09:00:00+08', 5, 33),
('mock-eval-v1', 1, 'data.export', 'data.export', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"data.export","result_id":"fixed-result-35"}',
 '2026-08-22 09:00:00+08', 5, 34),
('mock-eval-v1', 1, 'database.list_tables', 'database.list_tables', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"database.list_tables","result_id":"fixed-result-36"}',
 '2026-08-22 09:00:00+08', 5, 35),
('mock-eval-v1', 1, 'database.describe_table', 'database.describe_table', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"database.describe_table","result_id":"fixed-result-37"}',
 '2026-08-22 09:00:00+08', 5, 36),
('mock-eval-v1', 1, 'database.query', 'database.query', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"database.query","result_id":"fixed-result-38"}',
 '2026-08-22 09:00:00+08', 5, 37),
('mock-eval-v1', 1, 'metrics.get', 'metrics.get', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"metrics.get","result_id":"fixed-result-39"}',
 '2026-08-22 09:00:00+08', 5, 38),
('mock-eval-v1', 1, 'dashboard.get', 'dashboard.get', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"dashboard.get","result_id":"fixed-result-40"}',
 '2026-08-22 09:00:00+08', 5, 39),
('mock-eval-v1', 1, 'code.search', 'code.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"code.search","result_id":"fixed-result-41"}',
 '2026-08-22 09:00:00+08', 5, 40),
('mock-eval-v1', 1, 'code.read', 'code.read', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"code.read","result_id":"fixed-result-42"}',
 '2026-08-22 09:00:00+08', 5, 41),
('mock-eval-v1', 1, 'code.execute', 'code.execute', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"code.execute","result_id":"fixed-result-43"}',
 '2026-08-22 09:00:00+08', 5, 42),
('mock-eval-v1', 1, 'git.get_diff', 'git.get_diff', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"git.get_diff","result_id":"fixed-result-44"}',
 '2026-08-22 09:00:00+08', 5, 43),
('mock-eval-v1', 1, 'github.search_issues', 'github.search_issues', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"github.search_issues","result_id":"fixed-result-45"}',
 '2026-08-22 09:00:00+08', 5, 44),
('mock-eval-v1', 1, 'ci.get_status', 'ci.get_status', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"ci.get_status","result_id":"fixed-result-46"}',
 '2026-08-22 09:00:00+08', 5, 45),
('mock-eval-v1', 1, 'browser.open_page', 'browser.open_page', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"browser.open_page","result_id":"fixed-result-47"}',
 '2026-08-22 09:00:00+08', 5, 46),
('mock-eval-v1', 1, 'browser.click', 'browser.click', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"browser.click","result_id":"fixed-result-48"}',
 '2026-08-22 09:00:00+08', 5, 47),
('mock-eval-v1', 1, 'browser.fill_form', 'browser.fill_form', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"browser.fill_form","result_id":"fixed-result-49"}',
 '2026-08-22 09:00:00+08', 5, 48),
('mock-eval-v1', 1, 'computer.screenshot', 'computer.screenshot', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"computer.screenshot","result_id":"fixed-result-50"}',
 '2026-08-22 09:00:00+08', 5, 49),
('mock-eval-v1', 1, 'computer.upload_file', 'computer.upload_file', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"computer.upload_file","result_id":"fixed-result-51"}',
 '2026-08-22 09:00:00+08', 5, 50),
('mock-eval-v1', 1, 'weather.get_forecast', 'weather.get_forecast', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"weather.get_forecast","result_id":"fixed-result-52"}',
 '2026-08-22 09:00:00+08', 5, 51),
('mock-eval-v1', 1, 'maps.search_places', 'maps.search_places', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"maps.search_places","result_id":"fixed-result-53"}',
 '2026-08-22 09:00:00+08', 5, 52),
('mock-eval-v1', 1, 'maps.get_directions', 'maps.get_directions', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"maps.get_directions","result_id":"fixed-result-54"}',
 '2026-08-22 09:00:00+08', 5, 53),
('mock-eval-v1', 1, 'travel.search_transport', 'travel.search_transport', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"travel.search_transport","result_id":"fixed-result-55"}',
 '2026-08-22 09:00:00+08', 5, 54),
('mock-eval-v1', 1, 'travel.search_hotels', 'travel.search_hotels', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"travel.search_hotels","result_id":"fixed-result-56"}',
 '2026-08-22 09:00:00+08', 5, 55),
('mock-eval-v1', 1, 'travel.build_itinerary', 'travel.build_itinerary', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"travel.build_itinerary","result_id":"fixed-result-57"}',
 '2026-08-22 09:00:00+08', 5, 56),
('mock-eval-v1', 1, 'image.analyze', 'image.analyze', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"image.analyze","result_id":"fixed-result-58"}',
 '2026-08-22 09:00:00+08', 5, 57),
('mock-eval-v1', 1, 'image.generate', 'image.generate', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"image.generate","result_id":"fixed-result-59"}',
 '2026-08-22 09:00:00+08', 5, 58),
('mock-eval-v1', 1, 'image.edit', 'image.edit', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"image.edit","result_id":"fixed-result-60"}',
 '2026-08-22 09:00:00+08', 5, 59),
('mock-eval-v1', 1, 'ocr.extract_text', 'ocr.extract_text', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"ocr.extract_text","result_id":"fixed-result-61"}',
 '2026-08-22 09:00:00+08', 5, 60),
('mock-eval-v1', 1, 'design.create_mockup', 'design.create_mockup', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"design.create_mockup","result_id":"fixed-result-62"}',
 '2026-08-22 09:00:00+08', 5, 61),
('mock-eval-v1', 1, 'audio.transcribe', 'audio.transcribe', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"audio.transcribe","result_id":"fixed-result-63"}',
 '2026-08-22 09:00:00+08', 5, 62),
('mock-eval-v1', 1, 'audio.translate', 'audio.translate', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"audio.translate","result_id":"fixed-result-64"}',
 '2026-08-22 09:00:00+08', 5, 63),
('mock-eval-v1', 1, 'speech.generate', 'speech.generate', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"speech.generate","result_id":"fixed-result-65"}',
 '2026-08-22 09:00:00+08', 5, 64),
('mock-eval-v1', 1, 'video.summarize', 'video.summarize', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"video.summarize","result_id":"fixed-result-66"}',
 '2026-08-22 09:00:00+08', 5, 65),
('mock-eval-v1', 1, 'video.generate', 'video.generate', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"video.generate","result_id":"fixed-result-67"}',
 '2026-08-22 09:00:00+08', 5, 66),
('mock-eval-v1', 1, 'product.search', 'product.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"product.search","result_id":"fixed-result-68"}',
 '2026-08-22 09:00:00+08', 5, 67),
('mock-eval-v1', 1, 'product.compare', 'product.compare', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"product.compare","result_id":"fixed-result-69"}',
 '2026-08-22 09:00:00+08', 5, 68),
('mock-eval-v1', 1, 'product.get_price', 'product.get_price', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"product.get_price","result_id":"fixed-result-70"}',
 '2026-08-22 09:00:00+08', 5, 69),
('mock-eval-v1', 1, 'cart.add_item', 'cart.add_item', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"cart.add_item","result_id":"fixed-result-71"}',
 '2026-08-22 09:00:00+08', 5, 70),
('mock-eval-v1', 1, 'order.get_status', 'order.get_status', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"order.get_status","result_id":"fixed-result-72"}',
 '2026-08-22 09:00:00+08', 5, 71),
('mock-eval-v1', 1, 'crm.search_customer', 'crm.search_customer', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"crm.search_customer","result_id":"fixed-result-73"}',
 '2026-08-22 09:00:00+08', 5, 72),
('mock-eval-v1', 1, 'crm.get_account', 'crm.get_account', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"crm.get_account","result_id":"fixed-result-74"}',
 '2026-08-22 09:00:00+08', 5, 73),
('mock-eval-v1', 1, 'support.search_tickets', 'support.search_tickets', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"support.search_tickets","result_id":"fixed-result-75"}',
 '2026-08-22 09:00:00+08', 5, 74),
('mock-eval-v1', 1, 'support.create_ticket', 'support.create_ticket', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"support.create_ticket","result_id":"fixed-result-76"}',
 '2026-08-22 09:00:00+08', 5, 75),
('mock-eval-v1', 1, 'contacts.search', 'contacts.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"contacts.search","result_id":"fixed-result-77"}',
 '2026-08-22 09:00:00+08', 5, 76),
('mock-eval-v1', 1, 'notes.search', 'notes.search', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"notes.search","result_id":"fixed-result-78"}',
 '2026-08-22 09:00:00+08', 5, 77),
('mock-eval-v1', 1, 'calculator.evaluate', 'calculator.evaluate', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"calculator.evaluate","result_id":"fixed-result-79"}',
 '2026-08-22 09:00:00+08', 5, 78),
('mock-eval-v1', 1, 'translate.text', 'translate.text', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"translate.text","result_id":"fixed-result-80"}',
 '2026-08-22 09:00:00+08', 5, 79),
('mock-eval-v1', 1, 'health.search_guidance', 'health.search_guidance', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"health.search_guidance","result_id":"fixed-result-81"}',
 '2026-08-22 09:00:00+08', 5, 80),
('mock-eval-v1', 1, 'health.get_medication_info', 'health.get_medication_info', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"health.get_medication_info","result_id":"fixed-result-82"}',
 '2026-08-22 09:00:00+08', 5, 81),
('mock-eval-v1', 1, 'fitness.get_activity', 'fitness.get_activity', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"fitness.get_activity","result_id":"fixed-result-83"}',
 '2026-08-22 09:00:00+08', 5, 82),
('mock-eval-v1', 1, 'appointment.find_clinic', 'appointment.find_clinic', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"appointment.find_clinic","result_id":"fixed-result-84"}',
 '2026-08-22 09:00:00+08', 5, 83),
('mock-eval-v1', 1, 'learning.search_course', 'learning.search_course', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"learning.search_course","result_id":"fixed-result-85"}',
 '2026-08-22 09:00:00+08', 5, 84),
('mock-eval-v1', 1, 'learning.explain_topic', 'learning.explain_topic', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"learning.explain_topic","result_id":"fixed-result-86"}',
 '2026-08-22 09:00:00+08', 5, 85),
('mock-eval-v1', 1, 'quiz.create', 'quiz.create', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"quiz.create","result_id":"fixed-result-87"}',
 '2026-08-22 09:00:00+08', 5, 86),
('mock-eval-v1', 1, 'citation.lookup', 'citation.lookup', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"citation.lookup","result_id":"fixed-result-88"}',
 '2026-08-22 09:00:00+08', 5, 87),
('mock-eval-v1', 1, 'legal.search_policy', 'legal.search_policy', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"legal.search_policy","result_id":"fixed-result-89"}',
 '2026-08-22 09:00:00+08', 5, 88),
('mock-eval-v1', 1, 'legal.compare_clauses', 'legal.compare_clauses', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"legal.compare_clauses","result_id":"fixed-result-90"}',
 '2026-08-22 09:00:00+08', 5, 89),
('mock-eval-v1', 1, 'contract.extract_terms', 'contract.extract_terms', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"contract.extract_terms","result_id":"fixed-result-91"}',
 '2026-08-22 09:00:00+08', 5, 90),
('mock-eval-v1', 1, 'compliance.check_text', 'compliance.check_text', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"compliance.check_text","result_id":"fixed-result-92"}',
 '2026-08-22 09:00:00+08', 5, 91),
('mock-eval-v1', 1, 'device.list', 'device.list', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"device.list","result_id":"fixed-result-93"}',
 '2026-08-22 09:00:00+08', 5, 92),
('mock-eval-v1', 1, 'device.get_status', 'device.get_status', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"device.get_status","result_id":"fixed-result-94"}',
 '2026-08-22 09:00:00+08', 5, 93),
('mock-eval-v1', 1, 'device.set_state', 'device.set_state', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"device.set_state","result_id":"fixed-result-95"}',
 '2026-08-22 09:00:00+08', 5, 94),
('mock-eval-v1', 1, 'home.create_automation', 'home.create_automation', '{}',
 'SUCCESS', '{"mock":true,"status":"success","tool_name":"home.create_automation","result_id":"fixed-result-96"}',
 '2026-08-22 09:00:00+08', 5, 95)
;

-- ── 7. 负例冻结集 mock-eval-negative-v1(每方向空结果+ERROR 各 1;
--      web/file/mail/calendar 另补 TIMEOUT 各 1;共 42 行;金融侧负例
--      见 20260822-fixture-negative.sql) ─────────────────────────────────

INSERT INTO touchstone.fixture_sets (id, version, title, fixture_type, source_hash, public)
VALUES ('mock-eval-negative-v1', 1, '通用工具目录负例冻结返回(空结果/失败/超时)', 'STATIC',
        encode(digest('mock-eval negative tool fixtures v1', 'sha256'), 'hex'), false)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.fixture_tool_responses
    (fixture_set_id, fixture_set_version, call_key, tool_name, arguments,
     response_status, response, observed_at, simulated_latency_ms, sequence)
VALUES
('mock-eval-negative-v1', 1, 'web.search', 'web.search', '{}',
 'SUCCESS', '{"results":[]}',
 '2026-08-22 09:00:00+08', 5, 0),
('mock-eval-negative-v1', 1, 'web.open', 'web.open', '{}',
 'ERROR', '{"error":"page unreachable"}',
 '2026-08-22 09:00:00+08', 5, 1),
('mock-eval-negative-v1', 1, 'web.extract', 'web.extract', '{}',
 'TIMEOUT', '{"error":"page load timeout"}',
 '2026-08-22 09:00:00+08', 30000, 2),
('mock-eval-negative-v1', 1, 'file.search', 'file.search', '{}',
 'SUCCESS', '{"items":[]}',
 '2026-08-22 09:00:00+08', 5, 3),
('mock-eval-negative-v1', 1, 'file.read', 'file.read', '{}',
 'ERROR', '{"error":"path not found"}',
 '2026-08-22 09:00:00+08', 5, 4),
('mock-eval-negative-v1', 1, 'file.list', 'file.list', '{}',
 'TIMEOUT', '{"error":"folder scan timeout"}',
 '2026-08-22 09:00:00+08', 30000, 5),
('mock-eval-negative-v1', 1, 'drive.search', 'drive.search', '{}',
 'SUCCESS', '{"results":[]}',
 '2026-08-22 09:00:00+08', 5, 6),
('mock-eval-negative-v1', 1, 'drive.get_metadata', 'drive.get_metadata', '{}',
 'ERROR', '{"error":"file not found"}',
 '2026-08-22 09:00:00+08', 5, 7),
('mock-eval-negative-v1', 1, 'mail.search', 'mail.search', '{}',
 'SUCCESS', '{"messages":[]}',
 '2026-08-22 09:00:00+08', 5, 8),
('mock-eval-negative-v1', 1, 'mail.read', 'mail.read', '{}',
 'ERROR', '{"error":"message not found"}',
 '2026-08-22 09:00:00+08', 5, 9),
('mock-eval-negative-v1', 1, 'message.search', 'message.search', '{}',
 'TIMEOUT', '{"error":"message channel timeout"}',
 '2026-08-22 09:00:00+08', 30000, 10),
('mock-eval-negative-v1', 1, 'calendar.list_events', 'calendar.list_events', '{}',
 'SUCCESS', '{"events":[]}',
 '2026-08-22 09:00:00+08', 5, 11),
('mock-eval-negative-v1', 1, 'calendar.find_availability', 'calendar.find_availability', '{}',
 'ERROR', '{"error":"calendar service unavailable"}',
 '2026-08-22 09:00:00+08', 5, 12),
('mock-eval-negative-v1', 1, 'task.list', 'task.list', '{}',
 'TIMEOUT', '{"error":"task service timeout"}',
 '2026-08-22 09:00:00+08', 30000, 13),
('mock-eval-negative-v1', 1, 'spreadsheet.find_rows', 'spreadsheet.find_rows', '{}',
 'SUCCESS', '{"rows":[]}',
 '2026-08-22 09:00:00+08', 5, 14),
('mock-eval-negative-v1', 1, 'spreadsheet.read_range', 'spreadsheet.read_range', '{}',
 'ERROR', '{"error":"sheet not found"}',
 '2026-08-22 09:00:00+08', 5, 15),
('mock-eval-negative-v1', 1, 'database.list_tables', 'database.list_tables', '{}',
 'SUCCESS', '{"tables":[]}',
 '2026-08-22 09:00:00+08', 5, 16),
('mock-eval-negative-v1', 1, 'database.query', 'database.query', '{}',
 'ERROR', '{"error":"connection refused"}',
 '2026-08-22 09:00:00+08', 5, 17),
('mock-eval-negative-v1', 1, 'code.search', 'code.search', '{}',
 'SUCCESS', '{"matches":[]}',
 '2026-08-22 09:00:00+08', 5, 18),
('mock-eval-negative-v1', 1, 'code.read', 'code.read', '{}',
 'ERROR', '{"error":"file not in repository"}',
 '2026-08-22 09:00:00+08', 5, 19),
('mock-eval-negative-v1', 1, 'browser.open_page', 'browser.open_page', '{}',
 'SUCCESS', '{"content":""}',
 '2026-08-22 09:00:00+08', 5, 20),
('mock-eval-negative-v1', 1, 'browser.click', 'browser.click', '{}',
 'ERROR', '{"error":"element not found"}',
 '2026-08-22 09:00:00+08', 5, 21),
('mock-eval-negative-v1', 1, 'maps.search_places', 'maps.search_places', '{}',
 'SUCCESS', '{"places":[]}',
 '2026-08-22 09:00:00+08', 5, 22),
('mock-eval-negative-v1', 1, 'travel.search_transport', 'travel.search_transport', '{}',
 'ERROR', '{"error":"no route data"}',
 '2026-08-22 09:00:00+08', 5, 23),
('mock-eval-negative-v1', 1, 'ocr.extract_text', 'ocr.extract_text', '{}',
 'SUCCESS', '{"text":""}',
 '2026-08-22 09:00:00+08', 5, 24),
('mock-eval-negative-v1', 1, 'image.analyze', 'image.analyze', '{}',
 'ERROR', '{"error":"image not accessible"}',
 '2026-08-22 09:00:00+08', 5, 25),
('mock-eval-negative-v1', 1, 'audio.transcribe', 'audio.transcribe', '{}',
 'SUCCESS', '{"text":""}',
 '2026-08-22 09:00:00+08', 5, 26),
('mock-eval-negative-v1', 1, 'video.summarize', 'video.summarize', '{}',
 'ERROR', '{"error":"video not found"}',
 '2026-08-22 09:00:00+08', 5, 27),
('mock-eval-negative-v1', 1, 'product.search', 'product.search', '{}',
 'SUCCESS', '{"products":[]}',
 '2026-08-22 09:00:00+08', 5, 28),
('mock-eval-negative-v1', 1, 'order.get_status', 'order.get_status', '{}',
 'ERROR', '{"error":"order not found"}',
 '2026-08-22 09:00:00+08', 5, 29),
('mock-eval-negative-v1', 1, 'crm.search_customer', 'crm.search_customer', '{}',
 'SUCCESS', '{"customers":[]}',
 '2026-08-22 09:00:00+08', 5, 30),
('mock-eval-negative-v1', 1, 'support.search_tickets', 'support.search_tickets', '{}',
 'ERROR', '{"error":"ticket system unavailable"}',
 '2026-08-22 09:00:00+08', 5, 31),
('mock-eval-negative-v1', 1, 'contacts.search', 'contacts.search', '{}',
 'SUCCESS', '{"contacts":[]}',
 '2026-08-22 09:00:00+08', 5, 32),
('mock-eval-negative-v1', 1, 'notes.search', 'notes.search', '{}',
 'ERROR', '{"error":"notes index unavailable"}',
 '2026-08-22 09:00:00+08', 5, 33),
('mock-eval-negative-v1', 1, 'health.search_guidance', 'health.search_guidance', '{}',
 'SUCCESS', '{"results":[]}',
 '2026-08-22 09:00:00+08', 5, 34),
('mock-eval-negative-v1', 1, 'fitness.get_activity', 'fitness.get_activity', '{}',
 'ERROR', '{"error":"activity sync failed"}',
 '2026-08-22 09:00:00+08', 5, 35),
('mock-eval-negative-v1', 1, 'learning.search_course', 'learning.search_course', '{}',
 'SUCCESS', '{"courses":[]}',
 '2026-08-22 09:00:00+08', 5, 36),
('mock-eval-negative-v1', 1, 'citation.lookup', 'citation.lookup', '{}',
 'ERROR', '{"error":"identifier not resolved"}',
 '2026-08-22 09:00:00+08', 5, 37),
('mock-eval-negative-v1', 1, 'legal.search_policy', 'legal.search_policy', '{}',
 'SUCCESS', '{"policies":[]}',
 '2026-08-22 09:00:00+08', 5, 38),
('mock-eval-negative-v1', 1, 'contract.extract_terms', 'contract.extract_terms', '{}',
 'ERROR', '{"error":"document not accessible"}',
 '2026-08-22 09:00:00+08', 5, 39),
('mock-eval-negative-v1', 1, 'device.list', 'device.list', '{}',
 'SUCCESS', '{"devices":[]}',
 '2026-08-22 09:00:00+08', 5, 40),
('mock-eval-negative-v1', 1, 'device.get_status', 'device.get_status', '{}',
 'ERROR', '{"error":"device offline"}',
 '2026-08-22 09:00:00+08', 5, 41)
;

UPDATE touchstone.fixture_tool_responses
SET arguments_hash = 'sha256:' || encode(digest(arguments::text, 'sha256'), 'hex'),
    response_hash  = 'sha256:' || encode(digest(response::text, 'sha256'), 'hex')
WHERE fixture_set_id IN ('mock-eval-v1', 'mock-eval-negative-v1') AND fixture_set_version = 1;

ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN arguments_hash SET NOT NULL;
ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN response_hash SET NOT NULL;

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('20260822-generic-mock-tools.sql',
        'GT-6:通用工具目录 96 Mock 工具完整数据包——操作证8/工具集19/技能19/能力96(评测轴三列标注)/正例集 mock-eval-v1 96 行/负例集 mock-eval-negative-v1 42 行')
ON CONFLICT DO NOTHING;

COMMIT;

-- 执行后确认:
--   SELECT count(*) FROM touchstone.tool_capabilities;               -- 应 112(96+16)
--   SELECT side_effect, count(*) FROM touchstone.tool_capabilities
--     WHERE side_effect <> 'none' GROUP BY 1;                        -- write 8 / external_action 8
--   SELECT count(*) FROM touchstone.fixture_tool_responses
--     WHERE fixture_set_id='mock-eval-v1';                           -- 应 96
--   SELECT response_status, count(*) FROM touchstone.fixture_tool_responses
--     WHERE fixture_set_id='mock-eval-negative-v1' GROUP BY 1;       -- SUCCESS 19 / ERROR 19 / TIMEOUT 4
--   SELECT count(*) FROM touchstone.tool_skills WHERE enabled;       -- 应 0(金融技能照旧)
