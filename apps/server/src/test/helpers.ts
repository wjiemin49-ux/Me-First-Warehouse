import type { SuperAgentTest } from "supertest";
import { prisma } from "../lib/prisma";

type RegisterPayload = {
  email: string;
  password: string;
};

export async function resetDatabase() {
  await prisma.task.deleteMany();
  await prisma.project.deleteMany();
  await prisma.user.deleteMany();
}

export async function register(
  agent: SuperAgentTest,
  payload: RegisterPayload
) {
  return agent.post("/api/auth/register").send(payload);
}

export async function login(agent: SuperAgentTest, payload: RegisterPayload) {
  return agent.post("/api/auth/login").send(payload);
}

export async function registerAndLogin(
  agent: SuperAgentTest,
  payload: RegisterPayload
) {
  await register(agent, payload);
  return login(agent, payload);
}
