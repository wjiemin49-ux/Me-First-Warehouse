import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import App from "../../../App";

type ApiResponse<T> = {
  success: boolean;
  data: T;
  error: { message: string; code?: string } | null;
};

function apiResponse<T>(payload: ApiResponse<T>, ok = true): Response {
  return new Response(JSON.stringify(payload), {
    status: ok ? 200 : 400,
    headers: { "Content-Type": "application/json" }
  });
}

describe("ProjectSidebar", () => {
  beforeEach(() => {
    const projects = [
      { id: "p1", name: "Inbox" },
      { id: "p2", name: "Roadmap" }
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
        return apiResponse({ success: true, data: { projects }, error: null });
      }
      if (input === "/api/projects" && init?.method === "POST") {
        projects.push({ id: "p3", name: "Bugs" });
        return apiResponse({ success: true, data: { project: projects[2] }, error: null });
      }
      if (input === "/api/projects/p1" && init?.method === "PATCH") {
        projects[0] = { ...projects[0], name: "Inbox Renamed" };
        return apiResponse({ success: true, data: { project: projects[0] }, error: null });
      }
      if (input === "/api/projects/p2" && init?.method === "DELETE") {
        projects.splice(
          projects.findIndex((project) => project.id === "p2"),
          1
        );
        return apiResponse({ success: true, data: null, error: null });
      }
      if (input.startsWith("/api/tasks") && (!init?.method || init.method === "GET")) {
        return apiResponse({ success: true, data: { tasks: [] }, error: null });
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

  it("creates, renames, and deletes projects", async () => {
    render(<App />);

    await userEvent.type(screen.getByLabelText(/email/i), "demo@focusflow.dev");
    await userEvent.type(screen.getByLabelText(/^password$/i), "secret1234");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));

    await screen.findByRole("button", { name: "Inbox" });
    expect(screen.getByRole("button", { name: "Roadmap" })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/project name/i), "Bugs");
    await userEvent.click(screen.getByRole("button", { name: /add project/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Bugs" })).toBeInTheDocument();
    });

    const inboxRow = screen.getByRole("button", { name: "Inbox" }).closest("li");
    expect(inboxRow).not.toBeNull();

    await userEvent.click(within(inboxRow as HTMLElement).getByRole("button", { name: /rename/i }));
    await userEvent.clear(screen.getByLabelText(/rename project/i));
    await userEvent.type(screen.getByLabelText(/rename project/i), "Inbox Renamed");
    await userEvent.click(screen.getByRole("button", { name: /save project name/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Inbox Renamed" })).toBeInTheDocument();
    });

    const roadmapRow = screen.getByRole("button", { name: "Roadmap" }).closest("li");
    expect(roadmapRow).not.toBeNull();
    await userEvent.click(within(roadmapRow as HTMLElement).getByRole("button", { name: /delete/i }));

    await waitFor(() => {
      expect(screen.queryByText("Roadmap")).not.toBeInTheDocument();
    });
  });
});
