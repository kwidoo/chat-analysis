import React from "react";
import { render, screen, act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "../src/contexts/AuthContext";

// Mock fetch API
global.fetch = jest.fn();

// Helper component to test hooks
function TestComponent({ testAction }) {
  const auth = useAuth();

  return (
    <div>
      <div data-testid="loading">{auth.loading.toString()}</div>
      <div data-testid="isAuthenticated">{auth.isAuthenticated.toString()}</div>
      <div data-testid="user">{JSON.stringify(auth.user)}</div>
      <div data-testid="error">{auth.error || "no-error"}</div>

      <button
        data-testid="login-btn"
        onClick={() => auth.login("user@example.com", "password")}
      >
        Login
      </button>

      <button data-testid="logout-btn" onClick={auth.logout}>
        Logout
      </button>

      {testAction && (
        <button data-testid="test-action" onClick={testAction}>
          Test Action
        </button>
      )}
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    // Clear mocks and localStorage
    jest.clearAllMocks();
    localStorage.clear();
  });

  test("initial state with no stored tokens", async () => {
    // Setup fetch mock for initialization
    global.fetch.mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 401,
      })
    );

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    expect(screen.getByTestId("isAuthenticated").textContent).toBe("false");
    expect(screen.getByTestId("user").textContent).toBe("null");
    expect(screen.getByTestId("error").textContent).toBe("no-error");
  });

  test("restores authentication state from localStorage", async () => {
    // Setup valid tokens in localStorage
    localStorage.setItem("accessToken", "valid-token");
    localStorage.setItem("refreshToken", "valid-refresh-token");

    // Mock JWT payload verification (not expired)
    const mockJwtPayload = {
      exp: Math.floor(Date.now() / 1000) + 3600, // expires in 1 hour
    };

    global.atob = jest
      .fn()
      .mockImplementation(() => JSON.stringify(mockJwtPayload));

    // Mock API response for user info
    global.fetch.mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "123",
            email: "user@example.com",
            name: "Test User",
          }),
      })
    );

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
      expect(screen.getByTestId("isAuthenticated").textContent).toBe("true");
    });

    expect(screen.getByTestId("user").textContent).toContain(
      "user@example.com"
    );
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/auth/me",
      expect.any(Object)
    );
  });

  test("login process works correctly", async () => {
    // Mock successful login response
    global.fetch
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              access_token: "new-access-token",
              refresh_token: "new-refresh-token",
            }),
        })
      )
      .mockImplementationOnce(() =>
        // Mock user info response after login
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: "123",
              email: "user@example.com",
              name: "Test User",
            }),
        })
      );

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Click login button
    await act(async () => {
      userEvent.click(screen.getByTestId("login-btn"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("isAuthenticated").textContent).toBe("true");
    });

    // Verify localStorage was updated
    expect(localStorage.getItem("accessToken")).toBe("new-access-token");
    expect(localStorage.getItem("refreshToken")).toBe("new-refresh-token");

    // Verify user data was fetched
    expect(screen.getByTestId("user").textContent).toContain(
      "user@example.com"
    );
  });

  test("logout clears user and storage", async () => {
    // Setup initial logged-in state
    localStorage.setItem("accessToken", "valid-token");
    localStorage.setItem("refreshToken", "valid-refresh-token");

    global.fetch.mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "123",
            email: "user@example.com",
          }),
      })
    );

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Wait for initial authentication to complete
    await waitFor(() => {
      expect(screen.getByTestId("isAuthenticated").textContent).toBe("true");
    });

    // Reset fetch mock for logout request
    global.fetch.mockClear();
    global.fetch.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      })
    );

    // Click logout button
    await act(async () => {
      userEvent.click(screen.getByTestId("logout-btn"));
    });

    // Verify user is logged out
    await waitFor(() => {
      expect(screen.getByTestId("isAuthenticated").textContent).toBe("false");
      expect(screen.getByTestId("user").textContent).toBe("null");
    });

    // Verify localStorage was cleared
    expect(localStorage.getItem("accessToken")).toBeNull();
    expect(localStorage.getItem("refreshToken")).toBeNull();

    // Verify logout API was called
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.any(Object)
    );
  });

  test("token refresh works when token expires", async () => {
    // Setup a custom test action to trigger token refresh
    const refreshTokenAction = async () => {
      // Simulate a fetch call that will return 401
      try {
        const response = await fetch("/api/resource");
        return response.json();
      } catch (error) {
        return { error: error.message };
      }
    };

    // Setup initial logged-in state with an access token that will be detected as expired
    localStorage.setItem("accessToken", "expired-token");
    localStorage.setItem("refreshToken", "valid-refresh-token");

    // Mock JWT verification for expired token
    global.atob = jest.fn().mockImplementation(() =>
      JSON.stringify({
        exp: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
      })
    );

    // First fetch handles checking expired token
    // Second fetch will be the token refresh
    // Third fetch will be retrying the original request with new token
    // Fourth fetch will be the user info after token refresh
    global.fetch
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ message: "Unauthorized" }),
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              access_token: "new-access-token",
              refresh_token: "new-refresh-token",
            }),
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: "Success with new token" }),
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: "123",
              email: "user@example.com",
            }),
        })
      );

    render(
      <AuthProvider>
        <TestComponent testAction={refreshTokenAction} />
      </AuthProvider>
    );

    // Click the test action button to trigger a request that will need token refresh
    await act(async () => {
      userEvent.click(screen.getByTestId("test-action"));
    });

    // Verify localStorage was updated with new tokens
    await waitFor(() => {
      expect(localStorage.getItem("accessToken")).toBe("new-access-token");
      expect(localStorage.getItem("refreshToken")).toBe("new-refresh-token");
    });
  });
});
