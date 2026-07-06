import { Routes, Route } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import AuthenticatedShell from "./pages/AuthenticatedShell";

// No auth-guard logic yet (both routes render unconditionally) — 01-07-PLAN
// adds the redirect-on-401 guard once /api/health exists.
function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AuthenticatedShell />} />
    </Routes>
  );
}

export default App;
