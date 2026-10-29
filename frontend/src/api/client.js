import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.includes("/login")) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

export const login = (username, password) =>
  api.post("/api/auth/login", { username, password });

export const getCandidates = () => api.get("/api/candidates");
export const uploadCandidate = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/api/candidates", form);
};
export const deleteCandidate = (id) => api.delete(`/api/candidates/${id}`);

// Saved jobs: skills extracted once, every CV scored against them
export const listJobs = () => api.get("/api/jobs");
export const createJob = (title, description) => api.post("/api/jobs", { title, description });
export const getJob = (id) => api.get(`/api/jobs/${id}`);
export const updateJob = (id, data) => api.patch(`/api/jobs/${id}`, data);
export const deleteJob = (id) => api.delete(`/api/jobs/${id}`);
// rescoreAll=false scores only the CVs uploaded since the last search
export const runJobMatch = (id, rescoreAll = false) =>
  api.post(`/api/jobs/${id}/match`, null, { params: { rescore_all: rescoreAll } });

export const createInterview = (data) => api.post("/api/interviews", data);
export const getSession = (token) => api.get(`/api/interviews/${token}`);
export const getQuestions = (token) => api.post(`/api/interviews/${token}/questions`);
export const scoreAnswer = (token, question, answer) =>
  api.post(`/api/interviews/${token}/score`, { question, answer });
export const finishInterview = (token, payload) =>
  api.post(`/api/interviews/${token}/finish`, payload);

export const getDashboard = () => api.get("/api/dashboard/results");
export const acceptCandidate = (id) => api.post(`/api/dashboard/results/${id}/accept`);
export const rejectCandidate = (id) => api.post(`/api/dashboard/results/${id}/reject`);
