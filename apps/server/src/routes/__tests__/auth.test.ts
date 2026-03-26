import request from "supertest";
import { createApp } from "../../app";
import { resetDatabase } from "../../test/helpers";

describe("auth routes", () => {
  beforeEach(async () => {
    await resetDatabase();
  });

  test("POST /api/auth/register creates account and hides password hash", async () => {
    const app = createApp();

    const response = await request(app).post("/api/auth/register").send({
      email: "alice@example.com",
      password: "password123"
    });

    expect(response.status).toBe(201);
    expect(response.body.success).toBe(true);
    expect(response.body.error).toBeNull();
    expect(response.body.data.email).toBe("alice@example.com");
    expect(response.body.data.passwordHash).toBeUndefined();
    expect(response.body.data.id).toEqual(expect.any(String));
  });

  test("POST /api/auth/register rejects duplicate email with readable error", async () => {
    const app = createApp();
    await request(app).post("/api/auth/register").send({
      email: "dup@example.com",
      password: "password123"
    });

    const response = await request(app).post("/api/auth/register").send({
      email: "dup@example.com",
      password: "password123"
    });

    expect(response.status).toBe(409);
    expect(response.body.success).toBe(false);
    expect(response.body.data).toBeNull();
    expect(response.body.error.message).toMatch(/already/i);
  });

  test("POST /api/auth/login starts session for valid credentials", async () => {
    const app = createApp();
    const agent = request.agent(app);

    await agent.post("/api/auth/register").send({
      email: "login@example.com",
      password: "password123"
    });

    const response = await agent.post("/api/auth/login").send({
      email: "login@example.com",
      password: "password123"
    });

    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.error).toBeNull();
    expect(response.body.data.email).toBe("login@example.com");

    const projects = await agent.get("/api/projects");
    expect(projects.status).toBe(200);
    expect(projects.body.success).toBe(true);
  });

  test("POST /api/auth/login rejects invalid password", async () => {
    const app = createApp();
    await request(app).post("/api/auth/register").send({
      email: "wrong@example.com",
      password: "password123"
    });

    const response = await request(app).post("/api/auth/login").send({
      email: "wrong@example.com",
      password: "not-the-password"
    });

    expect(response.status).toBe(401);
    expect(response.body.success).toBe(false);
    expect(response.body.data).toBeNull();
    expect(response.body.error.message).toMatch(/invalid/i);
  });

  test("POST /api/auth/logout ends session and keeps response shape", async () => {
    const app = createApp();
    const agent = request.agent(app);

    await agent.post("/api/auth/register").send({
      email: "logout@example.com",
      password: "password123"
    });
    await agent.post("/api/auth/login").send({
      email: "logout@example.com",
      password: "password123"
    });

    const response = await agent.post("/api/auth/logout");

    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.error).toBeNull();
    expect(response.body.data).toEqual({ loggedOut: true });
  });
});
