import type { NextFunction, Request, Response } from "express";
import { HttpError } from "../lib/http-error";

export function requireAuth(req: Request, _res: Response, next: NextFunction) {
  const userId = req.session.userId;

  if (!userId) {
    return next(
      new HttpError(401, "Authentication required", { code: "UNAUTHORIZED" })
    );
  }

  req.userId = userId;
  return next();
}
