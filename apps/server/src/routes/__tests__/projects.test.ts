import request from "supertest";
import { createApp } from "../../app";
import {
  registerAndLogin,
  resetDatabase
} from "../../test/helpers";

describe("project routes", () => {
  beforeEach(async () => {
    await resetDatabase();
  });

  test("GET /api/projects requires authentication", async () => {
    const app = createApp();

    const response = await request(app).get("/api/projects");

    expect(response.status).toBe(401);
    expect(response.body).toMatchObject({
      success: false,
      data: null
    });
    expect(response.body.error.message).toMatch(/auth/i);
  });

  test("POST + GET /api/projects returns only current user projects", async () => {
    const app = createApp();
    const alice = request.agent(app);
    const bob = request.agent(app);

    await registerAndLogin(alice, {
      email: "alice-project@example.com",
      password: "password123"
    });
    await registerAndLogin(bob, {
      email: "bob-project@example.com",
      password: "password123"
    });

    await alice.post("/api/projects").send({ name: "Alice Project" });
    await bob.post("/api/projects").send({ name: "Bob Project" });

    const aliceList = await alice.get("/api/projects");

    expect(aliceList.status).toBe(200);
    expect(aliceList.body.success).toBe(true);
    expect(aliceList.body.error).toBeNull();
    expect(aliceList.body.data).toHaveLength(1);
    expect(aliceList.body.data[0].name).toBe("Alice Project");
  });

  test("PATCH /api/projects/:id updates own project", async () => {
    const app = createApp();
    const agent = request.agent(app);
    await registerAndLogin(agent, {
      email: "patch-project@example.com",
      password: "password123"
    });

    const created = await agent.post("/api/projects").send({ name: "Before" });
    const projectId = created.body.data.id as string;

    const response = await agent
      .patch(`/api/projects/${projectId}`)
      .send({ name: "After" });

    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.error).toBeNull();
    expect(response.body.data.name).toBe("After");
  });

  test("PATCH /api/projects/:id cannot update other user's project", async () => {
    const app = createApp();
    const owner = request.agent(app);
    const attacker = request.agent(app);

    await registerAndLogin(owner, {
      email: "owner@example.com",
      password: "password123"
    });
    await registerAndLogin(attacker, {
      email: "attacker@example.com",
      password: "password123"
    });

    const created = await owner.post("/api/projects").send({ name: "Secret" });
    const projectId = created.body.data.id as string;

    const response = await attacker
      .patch(`/api/projects/${projectId}`)
      .send({ name: "Hacked" });

    expect(response.status).toBe(404);
    expect(response.body.success).toBe(false);
    expect(response.body.data).toBeNull();
    expect(response.body.error.message).toMatch(/not found/i);
  });

  test("DELETE /api/projects/:id deletes own project", async () => {
    const app = createApp();
    const agent = request.agent(app);
    await registerAndLogin(agent, {
      email: "delete-project@example.com",
      password: "password123"
    });

    const created = await agent.post("/api/projects").send({ name: "Drop me" });
    const projectId = created.body.data.id as string;

    const deleted = await agent.delete(`/api/projects/${projectId}`);
    expect(deleted.status).toBe(200);
    expect(deleted.body.success).toBe(true);
    expect(deleted.body.data).toEqual({ deleted: true });

    const list = await agent.get("/api/projects");
    expect(list.body.data).toHaveLength(0);
  });
});
