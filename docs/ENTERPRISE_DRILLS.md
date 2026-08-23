# SupplyMind 企业级演练手册

本手册用于课堂、试运行和交付前演练。所有命令默认面向本地 Docker Compose 环境；生产环境必须先走变更审批、备份和回滚计划。

## 演练前准备

```powershell
docker compose up -d --build
docker compose ps
powershell -ExecutionPolicy Bypass -File scripts/acceptance-report.ps1
```

记录以下信息：

- 当前 Git commit。
- 当前 Alembic 版本。
- API ready 输出。
- 最近一次验收报告路径。

## D01 空环境复现

目标：证明学员能从空环境启动项目。

步骤：

```powershell
Copy-Item .env.example .env
powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1 -Build
docker compose exec -T api alembic current
```

验收：

- `api`、`worker`、`frontend`、`postgres`、`redis`、`minio` 健康。
- `/api/v1/health/live` 返回 `ok`。
- `/api/v1/health/ready` 返回 `ready`。
- 前端 `http://localhost:5173` 可登录。

## D02 Alembic 迁移与回滚

目标：训练显式迁移和安全回滚。

步骤：

```powershell
docker compose exec -T api alembic heads
docker compose exec -T api alembic current
docker compose exec -T api alembic history --verbose
```

回滚演练只允许在课堂环境执行：

```powershell
docker compose exec -T api alembic downgrade -1
docker compose exec -T api alembic upgrade head
docker compose exec -T api pytest -q
```

验收：

- `alembic heads` 只有一个 head。
- 回滚后能重新升级到 head。
- 测试通过。

注意：生产回滚必须先停止写入新字段的 API 版本，再回滚数据库；禁止直接删除数据库卷。

## D03 PostgreSQL RLS 与跨组织隔离

目标：证明多租户不是只靠前端隐藏。

步骤：

```powershell
docker compose exec -T api pytest -q tests/test_organization.py tests/test_reports.py tests/test_knowledge.py
```

浏览器验收：

- 使用 `admin@demo.local` 登录 `demo-factory`，确认能看到示范制造集团资源。
- 使用 `south-admin@demo.local` 登录 `demo-south`，确认只能看到南方制造事业部资源。
- 尝试通过 URL 深链访问另一组织资源，应返回无权限或 `404`。

验收：

- 跨组织资源不可见、不可下载、不可通过 SSE 或导出 ID 读取。
- 审计事件不泄露另一组织资源内容。

## D04 Redis 故障与任务恢复

目标：观察任务队列故障时的系统行为。

步骤：

```powershell
docker compose stop redis
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
docker compose start redis
```

恢复后：

```powershell
docker compose exec -T api pytest -q tests/test_task_watchdog.py
```

验收：

- ready 应明确显示依赖不可用或请求失败。
- Redis 恢复后 ready 重新通过。
- 任务不会静默成功；失败状态应可追踪。

## D05 MinIO/PDF 导出故障

目标：证明对象存储故障不会造成错误下载或假成功。

步骤：

```powershell
docker compose stop minio
```

浏览器中打开报告中心，尝试预览或导出 PDF。随后恢复：

```powershell
docker compose start minio
```

验收：

- PDF 导出失败时显示明确错误和 Trace ID。
- 报告列表仍可访问。
- 恢复 MinIO 后可重新导出或重试。

## D06 模型或 Embedding 不可用

目标：验证 AI 依赖 fail-closed。

步骤：

- 临时使用无效的 Chat 或 Embedding 配置启动课堂环境。
- 上传知识文档或发起分析。

验收：

- 不返回模拟结论。
- 不返回假向量或静态报告。
- 前端显示失败原因和 Trace ID。
- 审计或日志能定位到外部依赖失败。

## D07 数据源超时与危险 SQL

目标：验证只读分析边界。

步骤：

```powershell
docker compose exec -T api pytest -q tests/test_sql_guard.py tests/test_datasource_security.py
```

课堂讨论：

- 多语句为什么必须拒绝。
- `INSERT`、`UPDATE`、`DELETE`、DDL 为什么必须拒绝。
- 系统表和危险函数为什么不能开放给模型。
- 超时、行数和表白名单为什么是企业数据接入的最低要求。

验收：

- 危险 SQL 被结构化拒绝。
- 拒绝结果可审计。
- 前端不展示误导性的“分析成功”。

## D08 浏览器主路径回归

目标：证明系统仍能完成业务闭环。

步骤：

```powershell
$env:PLAYWRIGHT_BASE_URL="http://localhost:5173"
npm --prefix frontend run test:e2e
```

验收覆盖：

- 登录和深链。
- 桌面/移动导航。
- 管理员、分析师、只读成员权限。
- 第二组织资源隔离。
- 成员邀请。
- 数据源连接测试。
- 知识库生命周期。
- PDF 预览。
- 分析流式完成。

## D09 本地验收报告

目标：沉淀可交付证据。

轻量报告：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/acceptance-report.ps1
```

完整报告：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/acceptance-report.ps1 -RunTests -RunE2E -RunHelm
```

验收：

- 报告生成在 `output/acceptance`。
- 所有失败项有命令输出。
- 讲师或评审可复现报告中的检查。

## D10 备份与恢复讨论

课堂不要求真的连接生产备份系统，但必须能说清楚顺序：

1. 冻结发布窗口，记录 commit、镜像 tag 和 Alembic revision。
2. 备份 PostgreSQL 平台库。
3. 备份 MinIO/S3 报告和上传对象。
4. 执行迁移或发布。
5. 验证健康检查、登录、核心分析和 PDF 下载。
6. 失败时先回滚 API/Worker 镜像，再按兼容性决定是否 Alembic downgrade。
7. 恢复对象文件时必须保持数据库记录和对象 checksum 一致。

## 演练评分要点

- 是否能区分用户错误、依赖故障、权限拒绝和系统缺陷。
- 是否能通过 Trace ID、审计、系统状态和日志定位。
- 是否避免使用假数据掩盖真实故障。
- 是否能给出清晰的恢复顺序和验证命令。
