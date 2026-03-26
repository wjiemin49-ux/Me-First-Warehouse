export class HttpError extends Error {
  statusCode: number;
  code: string;
  details: unknown;

  constructor(
    statusCode: number,
    message: string,
    options?: {
      code?: string;
      details?: unknown;
    }
  ) {
    super(message);
    this.name = "HttpError";
    this.statusCode = statusCode;
    this.code = options?.code ?? "HTTP_ERROR";
    this.details = options?.details ?? null;
  }
}
