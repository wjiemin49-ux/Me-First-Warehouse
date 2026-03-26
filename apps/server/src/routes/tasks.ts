import { TaskStatus } from "@prisma/client";
import { Router } from "express";
import { z } from "zod";
import { HttpError } from "../lib/http-error";
import { prisma } from "../lib/prisma";
import { sendSuccess } from "../lib/response";
import { requireAuth } from "../middleware/auth";
import {
  taskCreateSchema,
  taskQuerySchema,
  taskUpdateSchema
} from "../validators/task";

const idParamSchema = z.object({
  id: z.string().min(1, "Task id is required")
});

async function ensureOwnedProject(projectId: string, userId: string) {
  const project = await prisma.project.findFirst({
    where: {
      id: projectId,
      userId
    }
  });
  if (!project) {
    throw new HttpError(404, "Project not found", {
      code: "PROJECT_NOT_FOUND"
    });
  }
}

export const tasksRouter = Router();

tasksRouter.use(requireAuth);

tasksRouter.get("/", async (req, res, next) => {
  try {
    const query = taskQuerySchema.parse(req.query);
    const now = new Date();

    const where = {
      project: {
        userId: req.userId
      },
      ...(query.projectId ? { projectId: query.projectId } : {}),
      ...(query.status ? { status: query.status } : {}),
      ...(query.q
        ? {
            OR: [
              { title: { contains: query.q } },
              { description: { contains: query.q } }
            ]
          }
        : {}),
      ...(query.overdue === "true"
        ? {
            dueDate: {
              lt: now
            },
            status: {
              not: TaskStatus.done
            }
          }
        : {})
    };

    const tasks = await prisma.task.findMany({
      where,
      orderBy: [
        {
          createdAt: "asc"
        }
      ]
    });

    return sendSuccess(res, tasks);
  } catch (error) {
    return next(error);
  }
});

tasksRouter.post("/", async (req, res, next) => {
  try {
    const payload = taskCreateSchema.parse(req.body);
    await ensureOwnedProject(payload.projectId, req.userId as string);

    const task = await prisma.task.create({
      data: {
        projectId: payload.projectId,
        title: payload.title,
        description: payload.description,
        status: payload.status,
        dueDate: payload.dueDate
      }
    });

    return sendSuccess(res, task, 201);
  } catch (error) {
    return next(error);
  }
});

tasksRouter.patch("/:id", async (req, res, next) => {
  try {
    const params = idParamSchema.parse(req.params);
    const payload = taskUpdateSchema.parse(req.body);

    const existing = await prisma.task.findFirst({
      where: {
        id: params.id,
        project: {
          userId: req.userId
        }
      }
    });
    if (!existing) {
      throw new HttpError(404, "Task not found", {
        code: "TASK_NOT_FOUND"
      });
    }

    if (payload.projectId) {
      await ensureOwnedProject(payload.projectId, req.userId as string);
    }

    const task = await prisma.task.update({
      where: {
        id: params.id
      },
      data: {
        ...payload,
        description: payload.description === null ? null : payload.description,
        dueDate: payload.dueDate === null ? null : payload.dueDate
      }
    });

    return sendSuccess(res, task);
  } catch (error) {
    return next(error);
  }
});

tasksRouter.delete("/:id", async (req, res, next) => {
  try {
    const params = idParamSchema.parse(req.params);

    const deleteResult = await prisma.task.deleteMany({
      where: {
        id: params.id,
        project: {
          userId: req.userId
        }
      }
    });
    if (deleteResult.count === 0) {
      throw new HttpError(404, "Task not found", {
        code: "TASK_NOT_FOUND"
      });
    }

    return sendSuccess(res, { deleted: true });
  } catch (error) {
    return next(error);
  }
});
