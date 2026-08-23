# SupplyMind

SupplyMind 是一个面向制造业供应链场景的多租户、只读 AI 数据分析控制台。项目用于演示企业级数据分析平台的完整开发方式：安全接入业务数据库，管理知识库口径，通过 AI 生成受控 SQL，返回可追溯的分析结果，并生成报告、审计和运行状态。

本项目是原创教学实现，架构设计参考企业级数据分析平台常见模式，不是 DB-GPT 的 fork，也不包含 DB-GPT 代码或品牌资源。

## 项目能力

- 多租户组织空间：组织、成员、角色、组织切换和跨组织隔离。
- 登录与权限：本地账号、刷新令牌、OIDC 接入入口、固定角色权限矩阵。
- 只读数据源：PostgreSQL/MySQL 连接测试、Schema 同步、表白名单、连接状态。
- SQL 安全：只允许单条 `SELECT` 或 `WITH`，禁止写操作、多语句、危险函数和越权表。
- 知识库：Markdown/TXT/PDF 上传、文本抽取、分块、Embedding、检索引用。
- AI 分析：数据源选择、知识库选择、八阶段 Agent 轨迹、SSE 流式状态、SQL Guard、结果表、图表和洞察。
- 报告中心：Markdown 报告、PDF 导出任务、MinIO/S3 对象存储、下载权限校验。
- 供应链大屏：采购交付、生产达成、库存健康、质量合格率、订单履约等指标。
- 审计与状态：Trace ID、审计筛选、系统状态、Worker 状态、失败任务和依赖健康。
- 工程交付：Docker Compose、Alembic、pytest、Ruff、Vitest、Playwright、Helm、CI 和安全扫描。

## 技术栈

- Backend：FastAPI、SQLAlchemy、Alembic、PostgreSQL/pgvector、Redis、Celery。
- Frontend：React、TypeScript、Vite、React Router、ECharts、Playwright。
- Storage：MinIO，本地模拟 S3 兼容对象存储。
- AI：OpenAI-compatible Chat API 和 Embedding API。
- DevOps：Docker Compose、Helm、GitHub Actions、Prometheus、Grafana。

## 环境要求

建议本机安装：

- Docker Desktop
- Git
- Node.js 22
- Python 3.12
- PowerShell

仅运行项目时，主要依赖 Docker Desktop。Node.js 和 Python 主要用于本机执行前端测试、Playwright 或生成密钥。

## 快速启动

克隆仓库后，在项目根目录执行：

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

等待容器启动后检查状态：

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/api/v1/health/live
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

访问地址：

- 前端控制台：`http://localhost:5173`
- API 文档：`http://localhost:8000/docs`
- MinIO 控制台：`http://localhost:9001`
- Prometheus：`http://localhost:9090`
- Grafana：`http://localhost:3000`

默认演示组织和账号：

| 角色 | 邮箱 | 组织 |
| --- | --- | --- |
| 组织管理员 | `admin@demo.local` | `demo-factory` |
| 分析师 | `analyst@demo.local` | `demo-factory` |
| 只读成员 | `viewer@demo.local` | `demo-factory` |
| 第二组织管理员 | `south-admin@demo.local` | `demo-south` |

本地演示密码：`ChangeMe123!`

生产或公开试运行环境禁止使用演示账号和默认密码。

## 密钥配置

项目不会提交真实密钥。首次运行时需要从 `.env.example` 复制出自己的 `.env`：

```powershell
Copy-Item .env.example .env
```

最重要的字段如下：

```dotenv
SUPPLYMIND_JWT_SECRET=replace-this-with-a-long-random-secret-at-least-32-characters
SUPPLYMIND_CREDENTIAL_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=

SUPPLYMIND_CHAT_BASE_URL=
SUPPLYMIND_CHAT_MODEL=
SUPPLYMIND_CHAT_API_KEY=

SUPPLYMIND_EMBEDDING_BASE_URL=
SUPPLYMIND_EMBEDDING_MODEL=
SUPPLYMIND_EMBEDDING_API_KEY=
```

生成本地随机 JWT 密钥：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

生成 Fernet 凭据加密密钥：

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

如果本机 Python 没有安装 `cryptography`，可以使用 API 镜像生成：

```powershell
docker compose build api
docker compose run --rm api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

真实 AI 分析需要填写 Chat 配置：

```dotenv
SUPPLYMIND_CHAT_BASE_URL=https://your-approved-chat-endpoint/v1
SUPPLYMIND_CHAT_MODEL=your-approved-chat-model
SUPPLYMIND_CHAT_API_KEY=your-chat-api-key
```

知识库向量化和 RAG 检索需要填写 Embedding 配置：

```dotenv
SUPPLYMIND_EMBEDDING_BASE_URL=https://your-approved-embedding-endpoint/v1
SUPPLYMIND_EMBEDDING_MODEL=your-approved-embedding-model
SUPPLYMIND_EMBEDDING_API_KEY=your-embedding-api-key
SUPPLYMIND_EMBEDDING_DIMENSION=1024
```

不配置 Chat 和 Embedding 时，登录、数据源、权限、报告列表、大屏和大部分界面仍可运行；真实分析、Embedding 和 RAG 检索会明确失败并返回 Trace ID，不会返回模拟结论。

完整配置说明见 [docs/CONFIGURATION.md](docs/CONFIGURATION.md)。

## 常用命令

启动完整环境：

```powershell
docker compose up -d --build
```

查看服务状态：

```powershell
docker compose ps
```

查看 API 日志：

```powershell
docker compose logs -f api
```

查看 Worker 日志：

```powershell
docker compose logs -f worker
```

停止环境：

```powershell
docker compose down
```

重置演示环境：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1 -Build
```

生成本地验收报告：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/acceptance-report.ps1 -RunTests
```

## 验收检查

后端测试：

```powershell
docker compose exec -T api pytest -q
docker compose exec -T api ruff check app scripts tests
```

前端测试和构建：

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

浏览器 E2E：

```powershell
$env:PLAYWRIGHT_BASE_URL="http://localhost:5173"
npm --prefix frontend run test:e2e
```

Compose 配置检查：

```powershell
docker compose config --quiet
```

Helm 模板检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/helm-smoke.ps1
```

## 目录结构

```text
backend/    FastAPI API、领域服务、Celery 任务、Alembic 迁移和后端测试
frontend/   React/TypeScript 控制台、页面、组件、API 客户端和浏览器测试
database/   演示数据、数据库说明和种子脚本
infra/      Prometheus、Grafana、Helm 和部署相关配置
docs/       配置、安全、API、部署、验收、回滚和企业演练文档
scripts/    本地验收、环境重置和 Helm 检查脚本
```

## 关键文档

- 配置与密钥：[docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- 架构说明：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- API 参考：[docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- 交付运行手册：[docs/DELIVERY_RUNBOOK.md](docs/DELIVERY_RUNBOOK.md)
- Helm 部署：[docs/HELM_DEPLOYMENT.md](docs/HELM_DEPLOYMENT.md)
- 回滚说明：[docs/ROLLBACK_RUNBOOK.md](docs/ROLLBACK_RUNBOOK.md)
- 验收清单：[docs/ACCEPTANCE_CHECKLIST.md](docs/ACCEPTANCE_CHECKLIST.md)

## 安全边界

- 只支持只读外部数据源账号。
- 数据源密码加密保存，不返回前端。
- 每个资源读取都必须带组织上下文，跨组织资源按 `404` 处理。
- AI 输出不能直接执行，必须经过 SQL Guard。
- Chat、Embedding、S3、OIDC 等密钥只能放在 `.env`、部署 Secret 或企业密钥管理系统。
- `.env`、`.env.trial`、真实密钥、客户数据导出和本地运行产物不得提交。

## 常见问题

### 1. 页面可以打开，但 AI 分析失败

检查 `.env` 中是否填写：

```dotenv
SUPPLYMIND_CHAT_BASE_URL=
SUPPLYMIND_CHAT_MODEL=
SUPPLYMIND_CHAT_API_KEY=
SUPPLYMIND_EMBEDDING_BASE_URL=
SUPPLYMIND_EMBEDDING_MODEL=
SUPPLYMIND_EMBEDDING_API_KEY=
```

没有配置模型时，系统会明确失败，这是预期行为。

### 2. API ready 不通过

先查看服务状态：

```powershell
docker compose ps
docker compose logs --tail=120 api
```

重点检查 PostgreSQL、Redis、MinIO 是否 healthy。

### 3. Playwright 提示缺少浏览器

在本机安装 Chromium：

```powershell
npx playwright install chromium
```

CI 中使用 `npx playwright install --with-deps chromium`。

### 4. 想重新开始演示数据

普通重启：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1 -Build
```

如果要连 Docker 卷一起清理，必须显式确认：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1 -WithVolumes -Build
```

这会删除本地演示数据，只能用于课堂或开发环境。

## License and notices

See [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md) for upstream references and dependency notice guidance.
