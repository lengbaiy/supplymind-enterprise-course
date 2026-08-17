# Helm 部署说明

Helm chart 位于 `infra/helm/supplymind`，默认只部署 API、Worker 和前端，不在集群内创建 PostgreSQL、Redis 或对象存储。

## Chart 校验

发布前必须执行 lint 和模板渲染。开发机不要求预装 Helm，可使用临时容器完成校验：

```powershell
docker run --rm -v "${PWD}:/work" -w /work alpine/helm:3.16.3 lint infra/helm/supplymind
docker run --rm -v "${PWD}:/work" -w /work alpine/helm:3.16.3 template supplymind infra/helm/supplymind > .helm-rendered.yaml
Remove-Item .helm-rendered.yaml -ErrorAction SilentlyContinue
```

如果 Docker Hub 暂时不可用，可在可访问镜像仓库中使用相同版本的 Helm 3.16 镜像；不得将渲染产物提交到仓库。

生产环境应先创建密钥并通过 `existingSecret` 注入，例如：

```bash
kubectl create secret generic supplymind-secrets \
  --from-literal=SUPPLYMIND_SECRET_KEY='change-me' \
  --from-literal=SUPPLYMIND_OPENAI_API_KEY='...' \
  --from-literal=SUPPLYMIND_S3_ACCESS_KEY='...' \
  --from-literal=SUPPLYMIND_S3_SECRET_KEY='...'
helm upgrade --install supplymind infra/helm/supplymind \
  --set configMap.SUPPLYMIND_DATABASE_URL='postgresql+psycopg://...' \
  --set configMap.SUPPLYMIND_REDIS_URL='redis://...' \
  --set configMap.SUPPLYMIND_S3_ENDPOINT='https://s3.example.com' \
  --set ingress.enabled=true
```

PostgreSQL 16 + pgvector、Redis、S3 兼容存储和 OIDC Provider 由企业平台提供；将其连接地址写入 ConfigMap，将凭据写入 Secret 或外部 Secret 管理器。API 使用 `/api/v1/health/live` 和 `/api/v1/health/ready` 探针，Worker 使用进程探针，前端使用 HTTP 探针。
