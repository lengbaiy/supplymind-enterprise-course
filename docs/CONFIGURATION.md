# SupplyMind 配置与密钥说明

本项目使用仓库根目录的 `.env` 作为本地 Docker Compose 配置文件。仓库只提交 `.env.example` 和 `.env.trial.example`，真实 `.env`、`.env.trial` 和任何生产密钥都不能提交。

## 快速配置

首次运行：

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

打开 `http://localhost:5173`，使用 `admin@demo.local`、`ChangeMe123!`、组织 `demo-factory` 登录。

不配置 Chat 和 Embedding 密钥时，平台、登录、数据源、报告列表和课程大部分功能仍可运行；真实 AI 分析、文档 Embedding 和 RAG 检索会明确失败并显示 Trace ID，不会返回模拟结论。

## 必须自己设置的密钥

在 `.env` 中修改以下字段：

| 变量 | 用途 | 本地课堂 | 试运行/生产 |
| --- | --- | --- | --- |
| `SUPPLYMIND_JWT_SECRET` | JWT 签名密钥 | 建议替换 | 必须替换 |
| `SUPPLYMIND_CREDENTIAL_KEY` | 数据源密码加密密钥，Fernet 格式 | 建议替换 | 必须替换 |
| `SUPPLYMIND_CHAT_API_KEY` | Chat 模型 API 密钥 | 需要真实分析时填写 | 必须由企业批准 |
| `SUPPLYMIND_EMBEDDING_API_KEY` | Embedding 模型 API 密钥 | 需要知识库检索时填写 | 必须由企业批准 |
| `SUPPLYMIND_S3_ACCESS_KEY` | MinIO/S3 访问密钥 | 可用本地默认 | 必须替换 |
| `SUPPLYMIND_S3_SECRET_KEY` | MinIO/S3 访问密钥 | 可用本地默认 | 必须替换 |
| `SUPPLYMIND_OIDC_CLIENT_SECRET` | 企业单点登录客户端密钥 | 可不配置 | 启用 OIDC 时必须填写 |

生成本地随机密钥：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

第一条结果填入 `SUPPLYMIND_JWT_SECRET`。第二条结果填入 `SUPPLYMIND_CREDENTIAL_KEY`。

如果本机 Python 没有安装 `cryptography`，可以先构建后使用 API 镜像生成 Fernet 密钥：

```powershell
docker compose build api
docker compose run --rm api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Chat 模型配置

真实分析需要 OpenAI-compatible Chat 接口。填写：

```dotenv
SUPPLYMIND_CHAT_BASE_URL=https://your-approved-chat-endpoint/v1
SUPPLYMIND_CHAT_MODEL=your-approved-chat-model
SUPPLYMIND_CHAT_API_KEY=your-chat-api-key
```

要求：

- `SUPPLYMIND_CHAT_BASE_URL` 必须包含兼容 API 前缀，以你的模型服务文档为准。
- `SUPPLYMIND_CHAT_MODEL` 必须是该服务已经开通的模型名。
- 密钥只写入 `.env`、部署 Secret 或企业密钥管理系统，不写入代码、文档提交或截图。

未配置或调用失败时，分析接口会 fail-closed，前端显示失败原因和 Trace ID。

## Embedding 配置

知识库上传后的向量化和检索需要 Embedding 接口。填写：

```dotenv
SUPPLYMIND_EMBEDDING_BASE_URL=https://your-approved-embedding-endpoint/v1
SUPPLYMIND_EMBEDDING_MODEL=your-approved-embedding-model
SUPPLYMIND_EMBEDDING_API_KEY=your-embedding-api-key
SUPPLYMIND_EMBEDDING_DIMENSION=1024
```

`SUPPLYMIND_EMBEDDING_DIMENSION` 必须和模型实际输出维度一致。维度不一致会导致向量写入或检索失败。

## 对象存储配置

本地 Docker Compose 默认启动 MinIO：

```dotenv
SUPPLYMIND_S3_ENDPOINT=http://minio:9000
SUPPLYMIND_S3_BUCKET=supplymind
SUPPLYMIND_S3_ACCESS_KEY=supplymind
SUPPLYMIND_S3_SECRET_KEY=change-this-in-production
```

本地课堂可以使用默认值。试运行和生产必须替换为企业对象存储或独立 MinIO 的真实凭据。

## OIDC 单点登录配置

本地账号登录不需要 OIDC。要启用企业单点登录，填写：

```dotenv
SUPPLYMIND_OIDC_ISSUER=https://your-idp.example.com
SUPPLYMIND_OIDC_CLIENT_ID=your-client-id
SUPPLYMIND_OIDC_CLIENT_SECRET=your-client-secret
SUPPLYMIND_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback
SUPPLYMIND_OIDC_AUTO_PROVISION=false
```

试运行和生产环境要把 `SUPPLYMIND_OIDC_REDIRECT_URI` 改为真实前端域名，例如：

```dotenv
SUPPLYMIND_OIDC_REDIRECT_URI=https://supplymind.example.com/auth/callback
```

## 数据源安全配置

数据源连接必须受主机和网段限制：

```dotenv
SUPPLYMIND_DATASOURCE_ALLOWED_HOSTS=localhost,127.0.0.1,demo-postgres,demo-mysql
SUPPLYMIND_DATASOURCE_ALLOWED_CIDRS=127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

课堂演示使用 Compose 网络内的 `demo-postgres` 和 `demo-mysql`。企业环境应只允许经过审批的数据库主机或网段，并且只使用只读账号。

## 试运行配置

试运行使用 `.env.trial.example`：

```powershell
Copy-Item .env.trial.example .env.trial
```

填完 `.env.trial` 后，按 [TRIAL_DEPLOYMENT.md](TRIAL_DEPLOYMENT.md) 启动。试运行会拒绝开发默认 JWT、默认凭据加密密钥和缺失的对象存储凭据。

## 密钥安全规则

- 不提交 `.env`、`.env.trial`、截图里的密钥或课程录屏里的密钥。
- 不把真实密钥写到 README、课件、Issue、Commit message 或聊天记录。
- 学员只能使用个人或课堂专用密钥，不能共用生产密钥。
- 密钥疑似泄露后，立即在模型服务、对象存储和身份提供商中轮换。
- 生产环境优先使用 Kubernetes Secret、云厂商 Secret Manager 或企业密钥管理系统。

## 配置验收

```powershell
docker compose up -d --build
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
powershell -ExecutionPolicy Bypass -File scripts/acceptance-report.ps1 -RunTests
```

需要完整浏览器验收时：

```powershell
$env:PLAYWRIGHT_BASE_URL="http://localhost:5173"
npm --prefix frontend run test:e2e
```
