import { Router, type Request } from "express";
import { HttpError } from "../lib/http-error";
import { hashPassword, verifyPassword } from "../lib/password";
import { prisma } from "../lib/prisma";
import { sendSuccess } from "../lib/response";
import { requireAuth } from "../middleware/auth";
import { authSchema } from "../validators/auth";

export const authRouter = Router();

async function regenerateSession(req: Request) {
  await new Promise<void>((resolve, reject) => {
    req.session.regenerate((error: Error | null) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

authRouter.post("/register", async (req, res, next) => {
  try {
    const payload = authSchema.parse(req.body);

    const exists = await prisma.user.findUnique({
      where: {
        email: payload.email
      }
    });
    if (exists) {
      throw new HttpError(409, "Email already registered", {
        code: "EMAIL_EXISTS"
      });
    }

    const passwordHash = await hashPassword(payload.password);
    const user = await prisma.user.create({
      data: {
        email: payload.email,
        passwordHash
      },
      select: {
        id: true,
        email: true
      }
    });

    await regenerateSession(req);
    req.session.userId = user.id;
    return sendSuccess(res, user, 201);
  } catch (error) {
    return next(error);
  }
});

authRouter.post("/login", async (req, res, next) => {
  try {
    const payload = authSchema.parse(req.body);

    const user = await prisma.user.findUnique({
      where: {
        email: payload.email
      }
    });
    if (!user) {
      throw new HttpError(401, "Invalid email or password", {
        code: "INVALID_CREDENTIALS"
      });
    }

    const valid = await verifyPassword(payload.password, user.passwordHash);
    if (!valid) {
      throw new HttpError(401, "Invalid email or password", {
        code: "INVALID_CREDENTIALS"
      });
    }

    await regenerateSession(req);
    req.session.userId = user.id;
    return sendSuccess(res, { id: user.id, email: user.email });
  } catch (error) {
    return next(error);
  }
});

authRouter.post("/logout", requireAuth, async (req, res, next) => {
  try {
    await new Promise<void>((resolve, reject) => {
      req.session.destroy((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      });
    });

    res.clearCookie("connect.sid");
    return sendSuccess(res, { loggedOut: true });
  } catch (error) {
    return next(error);
  }
});
