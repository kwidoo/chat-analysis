import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "../src/contexts/AuthContext";
import Dashboard from "../src/components/Dashboard";

// Mock recharts to avoid rendering issues in tests
jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  ComposedChart: ({ children }) => (
    <div data-testid="composed-chart">{children}</div>
  ),
  Line: () => <div data-testid="chart-line" />,
  Bar: () => <div data-testid="chart-bar" />,
  XAxis: () => <div data-testid="chart-xaxis" />,
  YAxis: () => <div data-testid="chart-yaxis" />,
  CartesianGrid: () => <div data-testid="chart-grid" />,
  Tooltip: () => <div data-testid="chart-tooltip" />,
  Legend: () => <div data-testid="chart-legend" />,
}));

// Create a protected route wrapper component
const ProtectedRoute = ({ children }) => {
  const auth = useAuth();
  return auth.isAuthenticated ? children : <Navigate to="/login" />;
};

// Setup component with AuthContext and routing
const renderDashboardWithAuth = (isAuthenticated = true) => {
  // Mock authentication context
  const mockAuthContext = {
    isAuthenticated,
    user: isAuthenticated ? { id: "123", name: "Test User" } : null,
    loading: false,
  };

  jest.mock("../src/contexts/AuthContext", () => ({
    ...jest.requireActual("../src/contexts/AuthContext"),
    useAuth: () => mockAuthContext,
  }));

  return render(
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

describe("Dashboard Component", () => {
  beforeEach(() => {
    // Clear mocks
    jest.clearAllMocks();

    // Mock fetch API
    global.fetch = jest.fn();
  });

  test("renders dashboard with visualization when authenticated", async () => {
    // Mock visualization data response
    global.fetch.mockImplementationOnce(() =>
      Promise.resolve({
        json: () =>
          Promise.resolve([
            { name: "Jan", messages: 65, sentiment: 0.8 },
            { name: "Feb", messages: 59, sentiment: 0.75 },
            { name: "Mar", messages: 80, sentiment: 0.9 },
          ]),
      })
    );

    renderDashboardWithAuth(true);

    // Check if dashboard content is rendered
    expect(screen.getByPlaceholderText(/search messages/i)).toBeInTheDocument();

    // Wait for data to load
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/visualization");
    });

    // Verify chart components are rendered
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    expect(screen.getByTestId("composed-chart")).toBeInTheDocument();
  });

  test("redirects to login when not authenticated", async () => {
    renderDashboardWithAuth(false);

    // Should redirect to login page
    await waitFor(() => {
      expect(screen.getByText(/login page/i)).toBeInTheDocument();
    });
  });

  test("search functionality sends request with query", async () => {
    // Mock API responses
    global.fetch.mockImplementation((url) => {
      if (url === "/api/visualization") {
        return Promise.resolve({
          json: () =>
            Promise.resolve([
              { name: "Jan", messages: 65, sentiment: 0.8 },
              { name: "Feb", messages: 59, sentiment: 0.75 },
            ]),
        });
      } else if (url === "/api/search") {
        return Promise.resolve({
          json: () =>
            Promise.resolve([
              { id: 1, title: "Test Result" },
              { id: 2, title: "Another Result" },
            ]),
        });
      }
      return Promise.reject(new Error("Not found"));
    });

    renderDashboardWithAuth(true);

    // Wait for initial data load
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/visualization");
    });

    // Enter search query
    const searchInput = screen.getByPlaceholderText(/search messages/i);
    await userEvent.type(searchInput, "test query");

    // Verify search request is made with correct parameters
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/search",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ q: "test query" }),
        })
      );
    });
  });

  test("handles API errors gracefully", async () => {
    // Mock API error response
    global.fetch.mockImplementationOnce(() =>
      Promise.reject(new Error("API error"))
    );

    // Suppress console.error for this test
    jest.spyOn(console, "error").mockImplementation(() => {});

    renderDashboardWithAuth(true);

    // Verify component doesn't crash
    expect(screen.getByPlaceholderText(/search messages/i)).toBeInTheDocument();
    expect(screen.getByText(/data visualization/i)).toBeInTheDocument();
  });
});
