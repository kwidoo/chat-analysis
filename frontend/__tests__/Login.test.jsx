import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "../src/contexts/AuthContext";
import Login from "../src/components/Login";

// Mock useNavigate
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => jest.fn(),
}));

// Setup component with AuthContext
const renderLoginWithContext = () => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

describe("Login Component", () => {
  beforeEach(() => {
    // Clear mocks and localStorage
    jest.clearAllMocks();
    localStorage.clear();

    // Mock fetch API
    global.fetch = jest.fn();
  });

  test("renders login form correctly", () => {
    renderLoginWithContext();

    // Check for form elements
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/don't have an account?/i)).toBeInTheDocument();
    expect(screen.getByText(/sign up/i)).toBeInTheDocument();
  });

  test("handles form submission with valid credentials", async () => {
    // Mock successful login response
    global.fetch
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              access_token: "test-access-token",
              refresh_token: "test-refresh-token",
            }),
        })
      )
      .mockImplementationOnce(() =>
        // Mock user info response
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: "123",
              email: "test@example.com",
            }),
        })
      );

    renderLoginWithContext();

    // Fill in form
    await userEvent.type(
      screen.getByLabelText(/email address/i),
      "test@example.com"
    );
    await userEvent.type(screen.getByLabelText(/password/i), "password123");

    // Submit form
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    // Verify form submission
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/auth/login",
        expect.any(Object)
      );
    });

    // Check that tokens were stored
    expect(localStorage.getItem("accessToken")).toBe("test-access-token");
    expect(localStorage.getItem("refreshToken")).toBe("test-refresh-token");
  });

  test("displays error message on login failure", async () => {
    // Mock failed login response
    global.fetch.mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        status: 401,
        json: () =>
          Promise.resolve({
            message: "Invalid email or password",
          }),
      })
    );

    renderLoginWithContext();

    // Fill in form
    await userEvent.type(
      screen.getByLabelText(/email address/i),
      "wrong@example.com"
    );
    await userEvent.type(screen.getByLabelText(/password/i), "wrongpassword");

    // Submit form
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    // Check for error message
    await waitFor(() => {
      expect(
        screen.getByText(/invalid email or password/i)
      ).toBeInTheDocument();
    });
  });

  test("handles MFA flow correctly", async () => {
    // Mock login response requiring MFA
    global.fetch
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              require_mfa: true,
              mfa_token: "test-mfa-token",
            }),
        })
      )
      .mockImplementationOnce(() =>
        // Mock MFA verification response
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              access_token: "mfa-access-token",
              refresh_token: "mfa-refresh-token",
            }),
        })
      )
      .mockImplementationOnce(() =>
        // Mock user info response after MFA
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: "123",
              email: "test@example.com",
            }),
        })
      );

    renderLoginWithContext();

    // Fill in login form
    await userEvent.type(
      screen.getByLabelText(/email address/i),
      "test@example.com"
    );
    await userEvent.type(screen.getByLabelText(/password/i), "password123");

    // Submit login form
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    // Verify MFA form is shown
    await waitFor(() => {
      expect(
        screen.getByText(/two-factor authentication/i)
      ).toBeInTheDocument();
      expect(screen.getByLabelText(/authentication code/i)).toBeInTheDocument();
    });

    // Fill in MFA code
    await userEvent.type(
      screen.getByLabelText(/authentication code/i),
      "123456"
    );

    // Submit MFA form
    fireEvent.click(screen.getByRole("button", { name: /verify/i }));

    // Verify MFA verification API was called
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/auth/verify-mfa",
        expect.any(Object)
      );
    });

    // Verify tokens after MFA success
    expect(localStorage.getItem("accessToken")).toBe("mfa-access-token");
    expect(localStorage.getItem("refreshToken")).toBe("mfa-refresh-token");
  });

  test("handles OAuth login correctly", async () => {
    // Create a spy on window.location.href
    const locationSpy = jest
      .spyOn(window.location, "href", "set")
      .mockImplementation(() => {});

    renderLoginWithContext();

    // Click OAuth login button
    fireEvent.click(
      screen.getByRole("button", { name: /sign in with google/i })
    );

    // Verify redirect to OAuth endpoint
    expect(locationSpy).toHaveBeenCalledWith("/api/auth/oauth/google");

    // Cleanup
    locationSpy.mockRestore();
  });
});
