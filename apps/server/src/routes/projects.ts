import { Router } from "express";
import { z } from "zod";
import { HttpError } from "../lib/http-error";
import { prisma } from "../lib/prisma";
import { sendSuccess } from "../lib/response";
import { requireAuth } from "../middleware/auth";
import {
  projectCreateSchema,
  projectUpdateSchema
} from "../validators/project";

const idParamSchema = z.object({
  id: z.string().min(1, "Project id is required")
});

export const projectsRouter = Router();

projectsRouter.use(requireAuth);

projectsRouter.get("/", async (req, res, next) => {
  try {
    const projects = await prisma.project.findMany({
      where: {
        userId: req.userId
      },
      orderBy: {
        createdAt: "asc"
      }
    });

    return sendSuccess(res, projects);
  } catch (error) {
    return next(error);
  }
});

projectsRouter.post("/", async (req, res, next) => {
  try {
    const payload = projectCreateSchema.parse(req.body);
    const project = await prisma.project.create({
      data: {
        name: payload.name,
        userId: req.userId as string
      }
    });

    return sendSuccess(res, project, 201);
  } catch (error) {
    return next(error);
  }
});

projectsRouter.patch("/:id", async (req, res, next) => {
  try {
    const params = idParamSchema.parse(req.params);
    const payload = projectUpdateSchema.parse(req.body);

    const updateResult = await prisma.project.updateMany({
      where: {
        id: params.id,
        userId: req.userId
      },
      data: {
        ...payload
      }
    });

    if (updateResult.count === 0) {
      throw new HttpError(404, "Project not found", {
        code: "PROJECT_NOT_FOUND"
      });
    }

    const updated = await prisma.project.findUnique({
      where: {
        id: params.id
      }
    });

    return sendSuccess(res, updated);
  } catch (error) {
    return next(error);
  }
});

projectsRouter.delete("/:id", async (req, res, next) => {
  try {
    const params = idParamSchema.parse(req.params);

    const deleteResult = await prisma.project.deleteMany({
      where: {
        id: params.id,
        userId: req.userId
      }
    });
    if (deleteResult.count === 0) {
      throw new HttpError(404, "Project not found", {
        code: "PROJECT_NOT_FOUND"
      });
    }

    return sendSuccess(res, { deleted: true });
  } catch (error) {
    return next(error);
  }
});
