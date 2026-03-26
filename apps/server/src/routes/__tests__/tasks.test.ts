import request from "supertest";
import { createApp } from "../../app";
import {
  registerAndLogin,
  resetDatabase
} from "../../test/helpers";

describe("task routes", () => {
  beforeEach(async () => {
    await resetDatabase();
  });

  test("POST /api/tasks creates task for own project", async () => {
    const app = createApp();
    const agent = request.agent(app);
    await registerAndLogin(agent, {
      email: "task-create@example.com",
      password: "password123"
    });

    const project = await agent.post("/api/projects").send({ name: "Main" });
    const projectId = project.body.data.id as string;

    const response = await agent.post("/api/tasks").send({
      projectId,
      title: "First Task",
      description: "Do something"
    });

    expect(response.status).toBe(201);
    expect(response.body.success).toBe(true);
    expect(response.body.error).toBeNull();
    expect(response.body.data.title).toBe("First Task");
    expect(response.body.data.status).toBe("todo");
  });

  test("POST /api/tasks blocks cross-user project access", async () => {
    const app = createApp();
    const owner = request.agent(app);
    const attacker = request.agent(app);
    await registerAndLogin(owner, {
      email: "task-owner@example.com",
      password: "password123"
    });
    await registerAndLogin(attacker, {
      email: "task-attacker@example.com",
      password: "password123"
    });

    const project = await owner.post("/api/projects").send({ name: "Owner P" });
    const projectId = project.body.data.id as string;

    const response = await attacker.post("/api/tasks").send({
      projectId,
      title: "Illegal task"
    });

    expect(response.status).toBe(404);
    expect(response.body.success).toBe(false);
    expect(response.body.error.message).toMatch(/project/i);
  });

  test("GET /api/tasks supports projectId/status/q/overdue filters", async () => {
    const app = createApp();
    const agent = request.agent(app);
    await registerAndLogin(agent, {
      email: "task-filter@example.com",
      password: "password123"
    });

    const projectA = await agent.post("/api/projects").send({ name: "A" });
    const projectB = await agent.post("/api/projects").send({ name: "B" });
    const projectAId = projectA.body.data.id as string;
    const projectBId = projectB.body.data.id as string;

    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();

    await agent.post("/api/tasks").send({
      projectId: projectAId,
      title: "Urgent bug",
      description: "contains keyword alpha",
      status: "in_progress",
      dueDate: yesterday
    });
    await agent.post("/api/tasks").send({
      projectId: projectAId,
      title: "Later work",
      status: "todo",
      dueDate: tomorrow
    });
    await agent.post("/api/tasks").send({
      projectId: projectBId,
      title: "Done item",
      description: "alpha complete",
      status: "done",
      dueDate: yesterday
    });

    const filtered = await agent.get(
      `/api/tasks?projectId=${projectAId}&status=in_progress&q=alpha&overdue=true`
    );

    expect(filtered.status).toBe(200);
    expect(filtered.body.success).toBe(true);
    expect(filtered.body.error).toBeNull();
    expect(filtered.body.data).toHaveLength(1);
    expect(filtered.body.data[0].title).toBe("Urgent bug");
  });

  test("PATCH /api/tasks/:id updates task fields and status", async () => {
    const app = createApp();
    const agent = request.agent(app);
    await registerAndLogin(agent, {
      email: "task-patch@example.com",
      password: "password123"
    });

    const project = await agent.post("/api/projects").send({ name: "Patch P" });
    const projectId = project.body.data.id as string;
    const created = await agent.post("/api/tasks").send({
      projectId,
      title: "Before",
      status: "todo"
    });
    const taskId = created.body.data.id as string;

    const response = await agent.patch(`/api/tasks/${taskId}`).send({
      title: "After",
      status: "done"
    });

    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.title).toBe("After");
    expect(response.body.data.status).toBe("done");
  });

  test("DELETE /api/tasks/:id enforces ownership", async () => {
    const app = createApp();
    const owner = request.agent(app);
    const attacker = request.agent(app);
    await registerAndLogin(owner, {
      email: "task-delete-owner@example.com",
      password: "password123"
    });
    await registerAndLogin(attacker, {
      email: "task-delete-attacker@example.com",
      password: "password123"
    });

    const project = await owner.post("/api/projects").send({ name: "Owner P2" });
    const created = await owner.post("/api/tasks").send({
      projectId: project.body.data.id as string,
      title: "Sensitive"
    });
    const taskId = created.body.data.id as string;

    const forbidden = await attacker.delete(`/api/tasks/${taskId}`);
    expect(forbidden.status).toBe(404);
    expect(forbidden.body.success).toBe(false);

    const allowed = await owner.delete(`/api/tasks/${taskId}`);
    expect(allowed.status).toBe(200);
    expect(allowed.body.success).toBe(true);
    expect(allowed.body.data).toEqual({ deleted: true });
  });
});
