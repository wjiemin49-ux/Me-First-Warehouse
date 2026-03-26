import { expect, test } from "@playwright/test";

const PASSWORD = process.env.E2E_PASSWORD ?? "FocusFlow#123";

function uniqueEmail(prefix) {
  const stamp = Date.now();
  const nonce = Math.random().toString(36).slice(2, 8);
  return `focusflow.${prefix}.${stamp}.${nonce}@example.com`;
}

async function openAuthPage(page) {
  await page.goto("/");
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
}

async function register(page, email) {
  await openAuthPage(page);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
}

async function login(page, email) {
  await openAuthPage(page);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
}

async function logout(page) {
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page.getByRole("button", { name: "Log in" })).toBeVisible();
}

async function createProject(page, projectName) {
  await page.getByLabel("Project name").fill(projectName);
  await page.getByRole("button", { name: "Add project" }).click();
  await expect(page.getByRole("button", { name: projectName })).toBeVisible();
}

async function createTask(page, taskTitle) {
  await page.getByLabel("Task title").fill(taskTitle);
  await page.getByRole("button", { name: "Add task" }).click();
  await expect(page.getByText(taskTitle)).toBeVisible();
}

async function switchTaskStatus(page, taskTitle) {
  const todoCard = page.getByTestId("column-todo").locator(".task-card", { hasText: taskTitle }).first();
  await expect(todoCard).toBeVisible();

  await todoCard.getByRole("button", { name: "Start" }).click();
  await expect(page.getByTestId("column-in_progress").getByText(taskTitle)).toBeVisible();

  const inProgressCard = page
    .getByTestId("column-in_progress")
    .locator(".task-card", { hasText: taskTitle })
    .first();
  await inProgressCard.getByRole("button", { name: "Mark done" }).click();
  await expect(page.getByTestId("column-done").getByText(taskTitle)).toBeVisible();
}

test.describe("FocusFlow E2E", () => {
  test("registers a new user", async ({ page }) => {
    const email = uniqueEmail("register");
    await register(page, email);
    await expect(page.getByText(`Welcome, ${email}`)).toBeVisible();
  });

  test("logs in with an existing account", async ({ page }) => {
    const email = uniqueEmail("login");
    await register(page, email);
    await logout(page);
    await login(page, email);
  });

  test("creates a task from the board", async ({ page }) => {
    const email = uniqueEmail("create-task");
    const projectName = `Project ${Date.now()}`;
    const taskTitle = `Task ${Date.now()}`;

    await register(page, email);
    await createProject(page, projectName);
    await createTask(page, taskTitle);
  });

  test("switches task status from todo to in_progress to done", async ({ page }) => {
    const email = uniqueEmail("status");
    const projectName = `Project ${Date.now()}`;
    const taskTitle = `Status ${Date.now()}`;

    await register(page, email);
    await createProject(page, projectName);
    await createTask(page, taskTitle);
    await switchTaskStatus(page, taskTitle);
  });
});
