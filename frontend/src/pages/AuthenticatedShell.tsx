import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

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

      <main className="mx-auto max-w-6xl px-lg py-2xl">
        {loading ? null : (
          <section className="max-w-2xl">
            <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
              You're signed in
            </h1>
            <p className="mt-sm text-sm leading-5 text-on-surface-variant">
              Document management features will appear here as they're built out. Come back once document types, templates, and the designer are live.
            </p>
          </section>
        )}
      </main>
    </div>
  );
}
