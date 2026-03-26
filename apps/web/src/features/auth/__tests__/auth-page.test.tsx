import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import App from "../../../App";

type MockResponse = {
  success: boolean;
  data: unknown;
  error: { message: string; code?: string } | null;
};

function jsonResponse(payload: MockResponse, ok = true): Response {
  return new Response(JSON.stringify(payload), {
    status: ok ? 200 : 400,
    headers: {
      "Content-Type": "application/json"
    }
  });
}

describe("AuthPage", () => {
  beforeEach(() => {
    const fetchMock = vi.fn(async (input: string, init?: RequestInit) => {
      if (input === "/api/auth/login" && init?.method === "POST") {
        return jsonResponse({
          success: true,
          data: { user: { id: "u1", email: "demo@focusflow.dev" } },
          error: null
        });
      }
      if (input === "/api/auth/register" && init?.method === "POST") {
        return jsonResponse({
          success: true,
          data: { user: { id: "u2", email: "new@focusflow.dev" } },
          error: null
        });
      }
      if (input === "/api/auth/logout" && init?.method === "POST") {
        return jsonResponse({ success: true, data: null, error: null });
      }
      return jsonResponse(
        {
          success: false,
          data: null,
          error: { message: "Unexpected endpoint in auth test" }
        },
        false
      );
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("logs in with labeled form fields and can logout", async () => {
    render(<App />);

    await userEvent.type(screen.getByLabelText(/email/i), "demo@focusflow.dev");
    await userEvent.type(screen.getByLabelText(/^password$/i), "secret1234");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    });

    const mock = vi.mocked(fetch);
    expect(mock).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        credentials: "include"
      })
    );

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));

    await waitFor(() => {
      expect(mock).toHaveBeenCalledWith(
        "/api/auth/logout",
        expect.objectContaining({
          method: "POST",
          credentials: "include"
        })
      );
    });
  });

  it("supports register mode and shows readable error messages", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementationOnce(async (input: string, init?: RequestInit) => {
      if (input === "/api/auth/register" && init?.method === "POST") {
        return jsonResponse(
          {
            success: false,
            data: null,
            error: { message: "Email already exists" }
          },
          false
        );
      }
      return jsonResponse({
        success: true,
        data: { user: { id: "u2", email: "new@focusflow.dev" } },
        error: null
      });
    });

    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    await userEvent.type(screen.getByLabelText(/email/i), "new@focusflow.dev");
    await userEvent.type(screen.getByLabelText(/^password$/i), "secret1234");
    await userEvent.click(screen.getByRole("button", { name: /register/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/email already exists/i);
    });
  });
});
