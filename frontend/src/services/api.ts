export class ApiError extends Error {
  status: number;
  traceId?: string;

  constructor(status: number, message: string, traceId?: string) {
    super(traceId ? `${message}（Trace ID: ${traceId}）` : message);
    this.name = "ApiError";
    this.status = status;
    this.traceId = traceId;
  }
}

export async function apiRequest<T>(
  baseUrl: string,
  token: string,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const headers: HeadersInit = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init?.body && !isFormData ? { "Content-Type": "application/json" } : {}),
    ...(init?.headers || {}),
  };
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = typeof payload.detail === "string" ? payload.detail : "请求失败";
    throw new ApiError(response.status, detail, response.headers.get("x-trace-id") || undefined);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
