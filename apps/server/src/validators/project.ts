import { z } from "zod";

export const projectCreateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Project name is required")
    .max(120, "Project name is too long")
});

export const projectUpdateSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, "Project name is required")
      .max(120, "Project name is too long")
      .optional()
  })
  .refine((value) => Object.keys(value).length > 0, {
    message: "At least one field is required"
  });
