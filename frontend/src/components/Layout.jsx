import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Upload, Briefcase, LayoutDashboard, LogOut } from "lucide-react";

const nav = [
  { to: "/upload",    label: "CV Upload",    icon: Upload },
  { to: "/match",     label: "Job Matcher",  icon: Briefcase },
  { to: "/dashboard", label: "Dashboard",    icon: LayoutDashboard },
];

export default function Layout() {
  const navigate = useNavigate();
  const logout = () => { localStorage.removeItem("token"); navigate("/login"); };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside style={{
        width: 220, background: "var(--surface)", borderRight: "1px solid var(--border)",
        display: "flex", flexDirection: "column", padding: "28px 0",
        flexShrink: 0, position: "sticky", top: 0, height: "100vh",
      }}>
        <div style={{ padding: "0 24px 32px" }}>
          <span style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 20, letterSpacing: "0.12em", textTransform: "uppercase" }}>
            REC<span style={{ color: "var(--gold)" }}>R</span>UTO
          </span>
        </div>

        <nav style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4, padding: "0 12px" }}>
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} style={({ isActive }) => ({
              display: "flex", alignItems: "center", gap: 10,
              padding: "10px 12px", borderRadius: "var(--radius)",
              color: isActive ? "var(--gold)" : "var(--text-mid)",
              background: isActive ? "var(--gold-dim)" : "transparent",
              fontWeight: isActive ? 600 : 400, fontSize: 14, transition: "all 0.15s",
            })}>
              <Icon size={16} />{label}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: "0 12px" }}>
          <button onClick={logout} className="btn-ghost"
            style={{ width: "100%", display: "flex", alignItems: "center", gap: 8, justifyContent: "center" }}>
            <LogOut size={15} /> Logout
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, padding: "40px 48px", overflowY: "auto" }}>
        <Outlet />
      </main>
    </div>
  );
}
