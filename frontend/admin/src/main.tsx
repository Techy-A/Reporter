import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "@pp/shared";
import "@pp/shared/src/tokens.css";
import "./admin.css";
import { AuthProvider, Gate } from "./auth";
import Shell from "./Shell";
import Setup from "./pages/Setup";
import Login from "./pages/Login";
import TwoFactor from "./pages/TwoFactor";
import Board from "./pages/Board";
import Rounds from "./pages/Rounds";
import People from "./pages/People";
import Settings from "./pages/Settings";
import Activity from "./pages/Activity";
import Helpdesk from "./pages/Helpdesk";
import Knowledge from "./pages/Knowledge";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/setup" element={<Gate want="needs-setup"><Setup /></Gate>} />
          <Route path="/login" element={<Gate want="signed-out"><Login /></Gate>} />
          <Route path="/two-factor" element={<Gate want="needs-mfa"><TwoFactor /></Gate>} />
          <Route element={<Gate want="signed-in"><Shell /></Gate>}>
            <Route index element={<Board />} />
            <Route path="rounds" element={<Rounds />} />
            <Route path="people" element={<People />} />
            <Route path="helpdesk" element={<Helpdesk />} />
            <Route path="answers" element={<Knowledge />} />
            <Route path="settings" element={<Settings />} />
            <Route path="activity" element={<Activity />} />
          </Route>
          <Route path="*" element={<Gate want="signed-in"><Shell /></Gate>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
