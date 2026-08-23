# SupplyMind 学员实验路线

本文件把完整项目拆成可教学、可验收、可回滚的企业级开发实验。每个实验都要求学员先阅读相关代码，再完成一个小的工程切片，并用自动化命令证明结果。

## 使用方式

- 学员路径：按 L01 到 L08 顺序完成，每个实验提交一个独立 commit。
- 讲师路径：每章开始前演示目标能力，结尾按验收命令检查。
- 分组建议：2 到 4 人一组，分别负责后端、前端、测试和交付记录。
- 完成标准：代码、测试、文档和验收截图或命令输出同时完成。

## 课前基线

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

登录地址：`http://localhost:5173`

演示账号：

- 组织管理员：`admin@demo.local`
- 分析师：`analyst@demo.local`
- 只读成员：`viewer@demo.local`
- 第二组织管理员：`south-admin@demo.local`

本地演示密码为 `ChangeMe123!`。生产环境禁止使用演示账号和默认密码。

## L01 架构边界与运行基线

目标：理解模块化单体、Docker Compose 依赖、API/Worker/Frontend 边界。

学员任务：

- 画出 API、Worker、PostgreSQL、Redis、MinIO、前端和演示数据源的运行关系。
- 找到 `/api/v1/health/live` 和 `/api/v1/health/ready` 的实现。
- 解释为什么客户数据源只能通过只读连接访问，不能挂载进应用容器。

验收命令：

```powershell
docker compose config --quiet
docker compose ps
Invoke-RestMethod http://localhost:8000/api/v1/health/live
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

提交建议：`docs: L01 architecture baseline notes`

## L02 身份、组织与权限隔离

目标：掌握 JWT、刷新令牌、组织上下文、角色矩阵和跨组织 `404` 语义。

学员任务：

- 为一个受保护接口补充权限测试。
- 使用管理员、分析师、只读成员分别访问成员管理和分析页面。
- 验证第二组织不能看到第一组织数据源、报告或分析运行。

验收命令：

```powershell
docker compose exec -T api pytest -q tests/test_organization.py
$env:PLAYWRIGHT_BASE_URL="http://localhost:5173"; npm --prefix frontend run test:e2e
```

提交建议：`test: L02 tenant permission regression`

## L03 只读数据源与 SQL Guard

目标：理解企业数据接入的安全边界：只读账号、主机/CIDR、表白名单、AST 校验、超时和审计。

学员任务：

- 新增一个被 SQL Guard 拒绝的危险 SQL 测试。
- 在浏览器中执行数据源连接测试和 Schema 查看。
- 说明为什么不能只依赖 Prompt 防止模型生成危险 SQL。

验收命令：

```powershell
docker compose exec -T api pytest -q tests/test_sql_guard.py tests/test_datasource_security.py
docker compose exec -T api ruff check app scripts tests
```

提交建议：`test: L03 extend sql guard coverage`

## L04 知识库、Embedding 与 RAG 引用

目标：完成文档上传、分块、Embedding、检索排序和引用追溯。

学员任务：

- 为一个新供应链指标补充知识库口径文档。
- 上传文档并观察摄取任务状态。
- 检索时返回文档名、chunk、位置和相似度。

验收命令：

```powershell
docker compose exec -T api pytest -q tests/test_knowledge.py tests/test_retrieval.py
```

浏览器验收：知识库页面创建知识库，上传文档，执行检索预览，确认引用位置可见。

提交建议：`feat: L04 add metric knowledge entry`

## L05 MCP 工具与八阶段 Agent

目标：理解模型输出不可信、工具契约可信、每个阶段可审计的 Agent 工程化方式。

学员任务：

- 阅读 MCP registry，选择一个工具说明其输入/输出 Schema。
- 新增一个只读工具契约或扩展现有工具测试。
- 运行一次分析，记录 SQL 草案、Guard 结果、查询行数、引用和报告 ID。

验收命令：

```powershell
docker compose exec -T api pytest -q tests/test_mcp_registry.py tests/test_agent_graph.py
```

提交建议：`test: L05 cover mcp tool contract`

## L06 异步任务、幂等与失败恢复

目标：掌握 Celery/Redis 任务状态机、幂等键、失败原因、重试和死信处理。

学员任务：

- 找到摄取、Schema 同步、分析和 PDF 导出的任务状态字段。
- 模拟一次依赖失败，观察系统状态页和 Trace ID。
- 解释哪些任务可以自动重试，哪些必须人工复核。

验收命令：

```powershell
docker compose exec -T api pytest -q tests/test_task_watchdog.py tests/test_runtime_safety.py
```

提交建议：`docs: L06 task recovery notes`

## L07 前端企业控制台

目标：掌握数据密集控制台的信息架构、权限态、加载态、空态、错误态和浏览器回归。

学员任务：

- 为一个页面补充空态或错误态。
- 保持桌面和移动导航可用。
- 用 Playwright 证明核心路径没有破坏。

验收命令：

```powershell
npm --prefix frontend test
npm --prefix frontend run build
$env:PLAYWRIGHT_BASE_URL="http://localhost:5173"; npm --prefix frontend run test:e2e
```

提交建议：`feat: L07 improve frontend state handling`

## L08 交付、CI、安全与回滚

目标：完成企业发布闭环：迁移、健康检查、CI、安全扫描、Helm、回滚和验收报告。

学员任务：

- 修复或新增一个 CI 检查。
- 运行本地验收报告脚本。
- 说明 Alembic 回滚和 MinIO/PostgreSQL 备份顺序。

验收命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/acceptance-report.ps1 -RunTests
powershell -ExecutionPolicy Bypass -File scripts/helm-smoke.ps1
```

提交建议：`ci: L08 harden delivery verification`

## 结课答辩

每组用 10 分钟展示：

- 一个真实分析运行 ID。
- SQL Guard 如何防止越权或危险查询。
- RAG 引用如何追溯到文档位置。
- 任务失败如何恢复或转人工。
- CI/CD 如何阻止有风险的改动进入发布。

答辩评分使用 [ASSESSMENT_RUBRIC.md](ASSESSMENT_RUBRIC.md)。
