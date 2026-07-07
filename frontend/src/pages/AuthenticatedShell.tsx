import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { type CurrentUser, fetchCurrentUser, logout } from "../lib/api";

export default function AuthenticatedShell() {
  const navigate = useNavigate();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      try {
        const currentUser = await fetchCurrentUser();
        if (cancelled) return;
        if (currentUser === null) {
          navigate("/login?error=session_expired");
          return;
        }
        setUser(currentUser);
      } catch {
        if (!cancelled) navigate("/login?error=session_expired");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadUser();

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const handleSignOut = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-background font-body text-on-surface">
      <header className="border-b border-outline-variant bg-surface-container">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-md px-lg py-md">
          <p className="font-headings text-lg font-bold text-primary">
            Precision Archival
          </p>
          {user ? (
            <div className="flex items-center gap-md">
              <span className="text-sm text-on-surface-variant">{user.email}</span>
              <button
                className="rounded border border-outline-variant px-md py-xs text-sm font-bold text-on-surface hover:border-outline hover:bg-surface-container-lowest"
                type="button"
                onClick={handleSignOut}
              >
                Sign Out
              </button>
            </div>
          ) : null}
        </div>
      </header>

      {loading ? null : (
        <div className="flex">
          <nav className="w-[280px] shrink-0 border-r border-outline-variant bg-surface-container-lowest">
            <div className="px-md py-lg">
            <NavLink
              to="/document-types"
              className={({ isActive }) =>
                `flex items-center gap-xs rounded px-sm py-xs text-sm font-bold ${
                  isActive
                      ? "bg-surface-container text-primary"
                      : "text-on-surface hover:bg-surface-container"
                  }`
                }
              >
                <span className="material-symbols-outlined text-[20px]">schema</span>
                Document Types
              </NavLink>
              <NavLink
                to="/content"
                className={({ isActive }) =>
                  `mt-sm flex items-center gap-xs rounded px-sm py-xs text-sm font-bold ${
                    isActive
                      ? "bg-surface-container text-primary"
                      : "text-on-surface hover:bg-surface-container"
                  }`
                }
              >
                <span className="material-symbols-outlined text-[20px]">library_books</span>
                Content Library
              </NavLink>
            </div>
          </nav>
          <main className="mx-auto max-w-6xl flex-1 px-lg py-2xl">
            <Outlet />
          </main>
        </div>
      )}
    </div>
  );
}
