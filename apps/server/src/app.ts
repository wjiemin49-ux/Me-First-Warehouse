import express from "express";
import session from "express-session";
import { env } from "./config/env";
import { errorHandler, notFoundHandler } from "./middleware/error-handler";
import { authRouter } from "./routes/auth";
import { projectsRouter } from "./routes/projects";
import { tasksRouter } from "./routes/tasks";

export function createApp() {
  const app = express();

  app.use(express.json());
  app.use(
    session({
      secret: env.sessionSecret,
      resave: false,
      saveUninitialized: false,
      cookie: {
        httpOnly: true,
        sameSite: "lax",
        secure: env.cookieSecure,
        maxAge: 1000 * 60 * 60 * 24 * 14
      }
    })
  );

  app.get("/health", (_req, res) => {
    res.status(200).json({ success: true, data: { status: "ok" }, error: null });
  });

  app.use("/api/auth", authRouter);
  app.use("/api/projects", projectsRouter);
  app.use("/api/tasks", tasksRouter);

  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}
