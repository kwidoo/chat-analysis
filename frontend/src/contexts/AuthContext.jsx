import React, {
  createContext,
  useState,
  useContext,
  useEffect,
  useCallback,
} from "react";

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check token expiry
  const isTokenExpired = (token) => {
    if (!token) return true;

    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      // Give 10 seconds buffer to avoid edge cases
      return payload.exp * 1000 < Date.now() - 10000;
    } catch (e) {
      return true;
    }
  };

  // Initialize - check if user is already logged in (via token in localStorage)
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const accessToken = localStorage.getItem("accessToken");
        const refreshToken = localStorage.getItem("refreshToken");

        if (accessToken && !isTokenExpired(accessToken)) {
          // Token valid, fetch user info
          const userInfo = await fetchUserInfo(accessToken);
          setUser(userInfo);
        } else if (refreshToken && !isTokenExpired(refreshToken)) {
          // Try to refresh the token
          await refreshAccessToken(refreshToken);
        }
      } catch (err) {
        console.error("Authentication initialization failed:", err);
        // Clear potentially invalid tokens
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  // Fetch user info from backend
  const fetchUserInfo = async (token) => {
    const response = await fetch("/api/auth/me", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) throw new Error("Failed to fetch user info");

    return response.json();
  };

  // Refresh access token
  const refreshAccessToken = useCallback(async (refreshToken) => {
    try {
      setLoading(true);
      const response = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) throw new Error("Token refresh failed");

      const data = await response.json();
      localStorage.setItem("accessToken", data.access_token);
      localStorage.setItem("refreshToken", data.refresh_token);

      // Update user info
      const userInfo = await fetchUserInfo(data.access_token);
      setUser(userInfo);
      return true;
    } catch (err) {
      console.error("Token refresh error:", err);
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      setUser(null);
      setError("Session expired. Please log in again.");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  // Handle login
  const login = async (email, password) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || "Login failed");
      }

      const data = await response.json();

      // Check if MFA is required
      if (data.require_mfa) {
        return { require_mfa: true, mfa_token: data.mfa_token };
      }

      // Store tokens
      localStorage.setItem("accessToken", data.access_token);
      localStorage.setItem("refreshToken", data.refresh_token);

      // Fetch user data
      const userInfo = await fetchUserInfo(data.access_token);
      setUser(userInfo);

      return { success: true };
    } catch (err) {
      console.error("Login error:", err);
      setError(err.message || "Login failed. Please try again.");
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  // Complete MFA verification
  const verifyMFA = async (mfaToken, mfaCode) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("/api/auth/verify-mfa", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ mfa_token: mfaToken, mfa_code: mfaCode }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || "MFA verification failed");
      }

      const data = await response.json();

      // Store tokens
      localStorage.setItem("accessToken", data.access_token);
      localStorage.setItem("refreshToken", data.refresh_token);

      // Fetch user data
      const userInfo = await fetchUserInfo(data.access_token);
      setUser(userInfo);

      return { success: true };
    } catch (err) {
      console.error("MFA verification error:", err);
      setError(err.message || "Verification failed. Please try again.");
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  // Handle registration
  const register = async (userData) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || "Registration failed");
      }

      return { success: true };
    } catch (err) {
      console.error("Registration error:", err);
      setError(err.message || "Registration failed. Please try again.");
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  // Handle OAuth login
  const oauthLogin = (provider) => {
    // Redirect to OAuth provider
    window.location.href = `/api/auth/oauth/${provider}`;
  };

  // Handle OAuth callback
  const handleOAuthCallback = async (params) => {
    try {
      const { token } = params;

      if (!token) {
        throw new Error("No token received from OAuth provider");
      }

      // Exchange token for JWT
      const response = await fetch("/api/auth/oauth/callback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ token }),
      });

      if (!response.ok) {
        throw new Error("Failed to authenticate with OAuth provider");
      }

      const data = await response.json();

      // Store tokens
      localStorage.setItem("accessToken", data.access_token);
      localStorage.setItem("refreshToken", data.refresh_token);

      // Fetch user data
      const userInfo = await fetchUserInfo(data.access_token);
      setUser(userInfo);

      return true;
    } catch (err) {
      console.error("OAuth callback error:", err);
      setError("OAuth authentication failed");
      return false;
    }
  };

  // Handle logout
  const logout = async () => {
    try {
      const refreshToken = localStorage.getItem("refreshToken");
      if (refreshToken) {
        // Optional: notify backend about logout to invalidate refresh token
        await fetch("/api/auth/logout", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      }
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      // Clear local storage regardless of server response
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      setUser(null);
    }
  };

  // Setup axios interceptor for automatic token refresh
  useEffect(() => {
    // Create axios response interceptor
    const setupInterceptors = () => {
      const originalFetch = window.fetch;
      window.fetch = async (...args) => {
        const [resource, config = {}] = args;

        // Try the request
        try {
          const response = await originalFetch(resource, config);
          // If response is 401 Unauthorized and we have a refresh token, try to refresh
          if (response.status === 401) {
            const refreshToken = localStorage.getItem("refreshToken");
            if (refreshToken && !isTokenExpired(refreshToken)) {
              const refreshed = await refreshAccessToken(refreshToken);

              if (refreshed) {
                // Retry the original request with new token
                const newConfig = {
                  ...config,
                  headers: {
                    ...config.headers,
                    Authorization: `Bearer ${localStorage.getItem(
                      "accessToken"
                    )}`,
                  },
                };
                return originalFetch(resource, newConfig);
              }
            }
          }
          return response;
        } catch (error) {
          return Promise.reject(error);
        }
      };
    };

    setupInterceptors();
  }, [refreshAccessToken]);

  const authContextValue = {
    user,
    loading,
    error,
    login,
    logout,
    register,
    verifyMFA,
    oauthLogin,
    handleOAuthCallback,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={authContextValue}>
      {children}
    </AuthContext.Provider>
  );
};
