import { StrictMode, useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { api, ErrorBoundary } from "@pp/shared";
import "@pp/shared/src/tokens.css";
import "./portal.css";
import SignIn from "./pages/SignIn";
import MyInterviews from "./pages/MyInterviews";
import MyData from "./pages/MyData";
import AskHR from "./pages/AskHR";
import Requests from "./pages/Requests";

export type Me = { name: string; email: string; organisation: string; is_interviewer: boolean };

function App() {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const refresh = useCallback(async () => {
    try {
      setMe(await api<Me>("/api/me"));
    } catch {
      setMe(null);
    }
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (me === undefined) return <div className="boot">Loading…</div>;
  if (me === null) {
    return (
      <Routes>
        <Route path="*" element={<SignIn onSignedIn={refresh} />} />
      </Routes>
    );
  }

  async function signOut() {
    await api("/api/auth/logout", { method: "POST" }).catch(() => {});
    setMe(null);
  }

  const initials = me.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="p-shell">
      <header className="p-top">
        <div className="p-brand">
          <span className="p-mark" aria-hidden>R</span>
          <span className="p-brand-name">Reporter</span>
          <span className="p-org">{me.organisation}</span>
        </div>
        <NavLink to="/my-data" className="p-avatar p-avatar-sm" aria-label="My data and sign out" title={me.name}>
          {initials}
        </NavLink>
      </header>
      <main className="p-main">
        <Routes>
          <Route index element={<AskHR me={me} />} />
          {me.is_interviewer && <Route path="interviews" element={<MyInterviews me={me} />} />}
          <Route path="requests" element={<Requests />} />
          <Route path="my-data" element={<MyData me={me} onSignOut={signOut} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <p className="trust p-foot">Self-hosted · you only see your own information</p>
      </main>
      <nav className="p-tabs" aria-label="Main">
        <NavLink to="/" end><TabIcon d="M4 5h16v11H8l-4 4zM8 9h8M8 12h5" />Ask HR</NavLink>
        {me.is_interviewer && (
          <NavLink to="/interviews"><TabIcon d="M3 5h18v16H3zM8 3v4M16 3v4M3 10h18" />Interviews</NavLink>
        )}
        <NavLink to="/requests"><TabIcon d="M4 4h16v16H4zM8 9h8M8 13h8M8 17h5" />Requests</NavLink>
        <NavLink to="/my-data"><TabIcon d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0" />My data</NavLink>
      </nav>
    </div>
  );
}

function TabIcon({ d }: { d: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d={d} /></svg>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
