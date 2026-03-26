import { z } from "zod";

export const authSchema = z.object({
  email: z.string().email("Email format is invalid"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(72, "Password is too long")
});
