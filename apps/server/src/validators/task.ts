import { TaskStatus } from "@prisma/client";
import { z } from "zod";

const dueDateSchema = z.preprocess((value) => {
  if (value === undefined || value === null || value === "") {
    return undefined;
  }
  if (value instanceof Date) {
    return value;
  }
  if (typeof value === "string" || typeof value === "number") {
    return new Date(value);
  }
  return value;
}, z.date().optional());

export const taskStatusSchema = z.nativeEnum(TaskStatus);

export const taskCreateSchema = z.object({
  projectId: z.string().min(1, "projectId is required"),
  title: z
    .string()
    .trim()
    .min(1, "Task title is required")
    .max(200, "Task title is too long"),
  description: z
    .string()
    .trim()
    .max(2000, "Task description is too long")
    .optional(),
  status: taskStatusSchema.optional(),
  dueDate: dueDateSchema
});

export const taskUpdateSchema = z
  .object({
    projectId: z.string().min(1, "projectId is required").optional(),
    title: z
      .string()
      .trim()
      .min(1, "Task title is required")
      .max(200, "Task title is too long")
      .optional(),
    description: z
      .string()
      .trim()
      .max(2000, "Task description is too long")
      .nullable()
      .optional(),
    status: taskStatusSchema.optional(),
    dueDate: dueDateSchema.nullable().optional()
  })
  .refine((value) => Object.keys(value).length > 0, {
    message: "At least one field is required"
  });

export const taskQuerySchema = z.object({
  projectId: z.string().optional(),
  status: taskStatusSchema.optional(),
  q: z.string().trim().optional(),
  overdue: z
    .enum(["true", "false"])
    .optional()
});
