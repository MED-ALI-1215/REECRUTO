import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";

import Login      from "./pages/Login";
import Upload     from "./pages/Upload";
import Match      from "./pages/Match";
import Dashboard  from "./pages/Dashboard";
import Interview  from "./pages/Interview";
import Layout     from "./components/Layout";

function RequireAuth({ children }) {
  return localStorage.getItem("token") ? children : <Navigate to="/login" replace />;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login"     element={<Login />} />
        <Route path="/interview" element={<Interview />} />

        {/* Recruiter (protected) */}
        <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index element={<Navigate to="/upload" replace />} />
          <Route path="upload"    element={<Upload />} />
          <Route path="match"     element={<Match />} />
          <Route path="dashboard" element={<Dashboard />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
