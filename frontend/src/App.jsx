import React from "react";
import { Routes, Route, Link, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Dashboard from "./components/Dashboard";
import SearchBar from "./components/SearchBar";
import Login from "./components/Login";
import Signup from "./components/Signup";
import ModelVersionControl from "./components/ModelVersionControl";
import QueueStatus from "./components/QueueStatus";

// Protected route wrapper component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login but save the intended destination
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return children;
};

// Main layout component with navigation for authenticated users
const AppLayout = ({ children }) => {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 font-sans">
      <header className="mb-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800">
            Text Analysis Dashboard
          </h1>

          {user && (
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Welcome, {user.first_name || user.email}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded-md"
              >
                Logout
              </button>
            </div>
          )}
        </div>

        {user && (
          <nav className="flex justify-center gap-3 my-5">
            <Link
              to="/upload"
              className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
            >
              Upload
            </Link>
            <Link
              to="/dashboard"
              className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
            >
              Dashboard
            </Link>
            <Link
              to="/search"
              className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
            >
              Search
            </Link>
            <Link
              to="/models"
              className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
            >
              Models
            </Link>
            <Link
              to="/queue"
              className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
            >
              Queue Status
            </Link>
          </nav>
        )}
      </header>
      {children}
    </div>
  );
};

// File upload component
const UploadForm = () => {
  const [files, setFiles] = React.useState([]);
  const [taskId, setTaskId] = React.useState(null);
  const [taskStatus, setTaskStatus] = React.useState(null);

  const handleFileChange = (event) => {
    setFiles(event.target.files);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
        },
        body: formData,
      });

      const result = await response.json();
      setTaskId(result.task_id);
      setTaskStatus("Processing started...");

      // Poll for status
      if (result.task_id) {
        pollTaskStatus(result.task_id);
      }
    } catch (error) {
      console.error("Upload error:", error);
      setTaskStatus("Upload failed");
    }
  };

  const pollTaskStatus = (id) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/status/${id}`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
          },
        });
        const data = await response.json();
        setTaskStatus(
          `Status: ${data.status} (Processed: ${
            data.queue_stats?.processed || 0
          }, Failed: ${data.queue_stats?.failed || 0})`
        );

        // If processing is complete, stop polling
        if (data.status === "completed") {
          clearInterval(interval);
        }
      } catch (error) {
        console.error("Status check error:", error);
        clearInterval(interval);
      }
    }, 2000);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-semibold mb-4">Upload Files</h2>
      <form onSubmit={handleSubmit} className="flex flex-col mb-4">
        <input
          type="file"
          multiple
          onChange={handleFileChange}
          className="mb-4"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors cursor-pointer"
        >
          Upload and Process
        </button>
      </form>
      {taskId && (
        <p className="p-3 bg-blue-50 border-l-4 border-blue-500 mb-4">
          Task ID: {taskId}
        </p>
      )}
      {taskStatus && (
        <p className="p-3 bg-blue-50 border-l-4 border-blue-500 mb-4">
          {taskStatus}
        </p>
      )}
    </div>
  );
};

function App() {
  const handleSearchResults = (results) => {
    console.log("Search results:", results);
    // You could update some state here to display the results in the UI
  };

  return (
    <AuthProvider>
      <AppContent handleSearchResults={handleSearchResults} />
    </AuthProvider>
  );
}

// Separate component to use hooks inside AuthProvider context
function AppContent({ handleSearchResults }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  return (
    <AppLayout>
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to={location.state?.from || "/dashboard"} replace />
            ) : (
              <Login />
            )
          }
        />
        <Route
          path="/signup"
          element={
            isAuthenticated ? (
              <Navigate to={location.state?.from || "/dashboard"} replace />
            ) : (
              <Signup />
            )
          }
        />

        {/* Protected routes */}
        <Route
          path="/upload"
          element={
            <ProtectedRoute>
              <UploadForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div className="bg-white p-6 rounded-lg shadow-md">
                <h2 className="text-2xl font-semibold mb-4">
                  Analysis Dashboard
                </h2>
                <Dashboard />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/search"
          element={
            <ProtectedRoute>
              <div className="bg-white p-6 rounded-lg shadow-md">
                <h2 className="text-2xl font-semibold mb-4">
                  Search Documents
                </h2>
                <SearchBar onSearch={handleSearchResults} />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/models"
          element={
            <ProtectedRoute>
              <div className="bg-white p-6 rounded-lg shadow-md">
                <h2 className="text-2xl font-semibold mb-4">
                  Model Management
                </h2>
                <ModelVersionControl />
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/queue"
          element={
            <ProtectedRoute>
              <div className="bg-white p-6 rounded-lg shadow-md">
                <h2 className="text-2xl font-semibold mb-4">
                  Processing Queue
                </h2>
                <QueueStatus />
              </div>
            </ProtectedRoute>
          }
        />

        {/* Redirect root to login or dashboard based on auth status */}
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />

        {/* Catch all - redirect to appropriate page based on auth status */}
        <Route
          path="*"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </AppLayout>
  );
}

export default App;
