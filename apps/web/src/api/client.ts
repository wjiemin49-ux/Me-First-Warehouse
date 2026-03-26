type ApiErrorPayload = {
  message: string;
  code?: string;
};

type ApiEnvelope<T> = {
  success: boolean;
  data: T;
  error: ApiErrorPayload | null;
};

export class ApiError extends Error {
  code?: string;

  constructor(message: string, code?: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}

function safeParseJson(input: string): unknown {
  if (!input) {
    return null;
  }

  try {
    return JSON.parse(input);
  } catch {
    return null;
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers
  });

  const bodyText = await response.text();
  const payload = safeParseJson(bodyText) as ApiEnvelope<T> | null;

  if (!payload || typeof payload !== "object" || !("success" in payload)) {
    const fallbackMessage = response.ok ? "Invalid API response format." : `Request failed (${response.status}).`;
    throw new ApiError(fallbackMessage);
  }

  if (!response.ok || payload.success === false) {
    const message =
      payload.error?.message ||
      `Request failed${response.status ? ` with status ${response.status}` : ""}.`;
    throw new ApiError(message, payload.error?.code);
  }

  return payload.data;
}
