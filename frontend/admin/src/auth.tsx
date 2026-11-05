import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, ApiError } from "@pp/shared";
import type { Me } from "./types";

type State =
  | { kind: "loading" }
  | { kind: "needs-setup" }
  | { kind: "signed-out" }
  | { kind: "needs-mfa" }
  | { kind: "signed-in"; me: Me };

const Ctx = createContext<{ state: State; refresh: () => Promise<void> }>({
  state: { kind: "loading" },
  refresh: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  const refresh = useCallback(async () => {
    try {
      const { setup_done } = await api<{ setup_done: boolean }>("/api/setup/status");
      if (!setup_done) return setState({ kind: "needs-setup" });
      const me = await api<Me>("/api/auth/me");
      setState({ kind: "signed-in", me });
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) return setState({ kind: "needs-mfa" });
      setState({ kind: "signed-out" });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return <Ctx.Provider value={{ state, refresh }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

export function useMe(): Me {
  const { state } = useAuth();
  if (state.kind !== "signed-in") throw new Error("useMe outside signed-in area");
  return state.me;
}

/** Sends people to the one screen their sign-in state allows. */
export function Gate({ want, children }: { want: State["kind"]; children: ReactNode }) {
  const { state } = useAuth();
  const loc = useLocation();
  if (state.kind === "loading") return <div className="boot">Loading…</div>;
  if (state.kind === want) return <>{children}</>;
  const to = {
    "needs-setup": "/setup",
    "signed-out": "/login",
    "needs-mfa": "/two-factor",
    "signed-in": "/",
    loading: "/",
  }[state.kind];
  return to === loc.pathname ? <>{children}</> : <Navigate to={to} replace />;
}
