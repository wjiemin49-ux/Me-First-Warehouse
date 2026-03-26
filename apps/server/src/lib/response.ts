import type { Response } from "express";

type ErrorPayload = {
  message: string;
  code?: string;
  details?: unknown;
};

export function sendSuccess<T>(res: Response, data: T, statusCode = 200) {
  return res.status(statusCode).json({
    success: true,
    data,
    error: null
  });
}

export function sendError(
  res: Response,
  error: ErrorPayload,
  statusCode = 400
) {
  return res.status(statusCode).json({
    success: false,
    data: null,
    error: {
      message: error.message,
      code: error.code ?? "ERROR",
      details: error.details ?? null
    }
  });
}
