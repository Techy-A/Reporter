import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "@pp/shared";
import { useAuth, useMe } from "./auth";

const NAV = [
  { to: "/", label: "Scheduling board", end: true },
  { to: "/rounds", label: "Interview rounds" },
  { to: "/people", label: "Interviewers & team" },
  { to: "/settings", label: "Settings" },
];

export default function Shell() {
  const me = useMe();
  const { refresh } = useAuth();
  const nav = useNavigate();

  async function signOut() {
    await api("/api/auth/logout", { method: "POST" }).catch(() => {});
    await refresh();
    nav("/login");
  }

  return (
    <div className="shell">
      <aside className="rail-nav">
        <div className="brand">
          <span className="brand-mark" aria-hidden>R</span>
          <div>
            <div className="brand-name">Reporter</div>
            <div className="brand-tag">Admin</div>
          </div>
        </div>
        <nav aria-label="Main">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
              {n.label}
            </NavLink>
          ))}
          {me.role === "owner" && (
            <NavLink to="/activity" className="nav-link">Activity log</NavLink>
          )}
        </nav>
        <div className="rail-foot">
          <div className="small who" title={me.email}>{me.email}</div>
          <div className="small muted">{me.role === "owner" ? "Owner" : "Recruiter"}</div>
          <button className="btn btn-ghost btn-sm" onClick={signOut}>Sign out</button>
          <div className="trust">Self-hosted · data stays on your server</div>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
