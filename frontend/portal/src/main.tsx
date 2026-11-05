import { StrictMode, useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { api, ErrorBoundary } from "@pp/shared";
import "@pp/shared/src/tokens.css";
import "./portal.css";
import SignIn from "./pages/SignIn";
import MyInterviews from "./pages/MyInterviews";
import MyData from "./pages/MyData";

export type Me = { name: string; email: string; organisation: string };

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

  return (
    <div className="p-shell">
      <header className="p-top">
        <div className="p-brand">
          <span className="p-mark" aria-hidden>P</span>
          <span>{me.organisation}</span>
        </div>
        <nav className="p-nav" aria-label="Main">
          <NavLink to="/" end>My interviews</NavLink>
          <NavLink to="/my-data">My data</NavLink>
        </nav>
      </header>
      <main className="p-main">
        <Routes>
          <Route index element={<MyInterviews me={me} />} />
          <Route path="my-data" element={<MyData me={me} onSignOut={signOut} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="p-foot trust">Employee portal · you only see your own information</footer>
    </div>
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
