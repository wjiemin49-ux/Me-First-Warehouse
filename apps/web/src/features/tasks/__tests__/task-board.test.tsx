import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import App from "../../../App";
import type { Task } from "../../../types";

type ApiShape<T> = {
  success: boolean;
  data: T;
  error: { message: string; code?: string } | null;
};

function apiResponse<T>(payload: ApiShape<T>, ok = true): Response {
  return new Response(JSON.stringify(payload), {
    status: ok ? 200 : 400,
    headers: { "Content-Type": "application/json" }
  });
}

describe("TaskBoard", () => {
  beforeEach(() => {
    const project = { id: "p1", name: "Main Project" };
    const tasks: Task[] = [
      {
        id: "t1",
        title: "Write docs",
        description: "",
        status: "todo",
        dueDate: "2000-01-01T00:00:00.000Z",
        projectId: "p1"
      }
    ];

    const fetchMock = vi.fn(async (input: string, init?: RequestInit) => {
      if (input === "/api/auth/login" && init?.method === "POST") {
        return apiResponse({
          success: true,
          data: { user: { id: "u1", email: "demo@focusflow.dev" } },
          error: null
        });
      }
      if (input === "/api/projects" && (!init?.method || init.method === "GET")) {
        return apiResponse({ success: true, data: { projects: [project] }, error: null });
      }
      if (input.startsWith("/api/tasks") && (!init?.method || init.method === "GET")) {
        return apiResponse({ success: true, data: { tasks }, error: null });
      }
      if (input === "/api/tasks" && init?.method === "POST") {
        tasks.push({
          id: "t2",
          title: "New task",
          description: "",
          status: "todo",
          dueDate: null,
          projectId: "p1"
        });
        return apiResponse({
          success: true,
          data: {
            task: tasks[tasks.length - 1]
          },
          error: null
        });
      }
      if (input === "/api/tasks/t1" && init?.method === "PATCH") {
        tasks[0] = { ...tasks[0], status: "in_progress" };
        return apiResponse({ success: true, data: { task: tasks[0] }, error: null });
      }
      return apiResponse(
        { success: false, data: null, error: { message: `Unhandled route: ${input}` } },
        false
      );
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("supports task create, status switch, and filters on kanban board", async () => {
    render(<App />);

    await userEvent.type(screen.getByLabelText(/email/i), "demo@focusflow.dev");
    await userEvent.type(screen.getByLabelText(/^password$/i), "secret1234");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));

    await screen.findByRole("heading", { name: /to do/i });
    expect(screen.getByRole("heading", { name: /in progress/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /done/i })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/task title/i), "New task");
    await userEvent.click(screen.getByRole("button", { name: /add task/i }));

    await waitFor(() => {
      expect(screen.getByText("New task")).toBeInTheDocument();
    });

    const todoColumn = screen.getByTestId("column-todo");
    const inProgressColumn = screen.getByTestId("column-in_progress");
    const taskCard = within(todoColumn).getByText("Write docs").closest("article");
    expect(taskCard).not.toBeNull();

    await userEvent.click(within(taskCard as HTMLElement).getByRole("button", { name: /start/i }));

    await waitFor(() => {
      expect(within(inProgressColumn).getByText("Write docs")).toBeInTheDocument();
    });

    await userEvent.selectOptions(screen.getByLabelText(/status filter/i), "in_progress");
    expect(screen.queryByText("New task")).not.toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText(/keyword/i));
    await userEvent.type(screen.getByLabelText(/keyword/i), "Write");
    expect(screen.getByText("Write docs")).toBeInTheDocument();

    await userEvent.click(screen.getByLabelText(/overdue only/i));
    expect(screen.getByText("Write docs")).toBeInTheDocument();
  });
});
