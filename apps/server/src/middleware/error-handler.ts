import { Prisma } from "@prisma/client";
import type { NextFunction, Request, Response } from "express";
import { ZodError } from "zod";
import { HttpError } from "../lib/http-error";
import { sendError } from "../lib/response";

export function notFoundHandler(_req: Request, res: Response) {
  return sendError(
    res,
    {
      message: "Route not found",
      code: "ROUTE_NOT_FOUND"
    },
    404
  );
}

export function errorHandler(
  error: unknown,
  _req: Request,
  res: Response,
  _next: NextFunction
) {
  if (error instanceof HttpError) {
    const httpError = error as HttpError;
    return sendError(
      res,
      {
        message: httpError.message,
        code: httpError.code,
        details: httpError.details
      },
      httpError.statusCode
    );
  }

  if (error instanceof ZodError) {
    return sendError(
      res,
      {
        message: "Validation failed",
        code: "VALIDATION_ERROR",
        details: error.flatten()
      },
      400
    );
  }

  if (error instanceof Prisma.PrismaClientKnownRequestError) {
    if (error.code === "P2002") {
      return sendError(
        res,
        {
          message: "Resource already exists",
          code: "CONFLICT"
        },
        409
      );
    }
  }

  if (error instanceof Error) {
    return sendError(
      res,
      {
        message: error.message,
        code: "INTERNAL_ERROR"
      },
      500
    );
  }

  return sendError(
    res,
    {
      message: "Unknown server error",
      code: "INTERNAL_ERROR"
    },
    500
  );
}
