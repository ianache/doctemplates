import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { type CurrentUser, fetchCurrentUser, logout } from "../lib/api";


const ROUTE_LABELS: Record<string, string> = {
  "document-types": "Document Types",
  "document-designs": "Document Designs",
  "document-issuances": "Documents Library",
  "generation-jobs": "Generation Jobs",
  content: "Content Library",
  new: "New",
  versions: "Version History",
  templates: "Templates",
  "static-pdfs": "Static PDFs",
  "xlsx-templates": "XLSX Templates",
  static: "Static PDFs",
  upload: "Upload",
};

function initialsFromEmail(email: string): string {
  if (!email) return "?";
  const [local] = email.split("@");
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return local.slice(0, 2).toUpperCase();
}

function buildBreadcrumbs(pathname: string): { label: string; to: string }[] {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return [];
  const crumbs: { label: string; to: string }[] = [];
  let acc = "";
  for (const seg of segments) {
    acc += `/${seg}`;
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(seg);
    const label = ROUTE_LABELS[seg] ?? (isUuid ? seg.slice(0, 8) + "…" : seg);
    crumbs.push({ label, to: acc });
  }
  return crumbs;
}

export default function AuthenticatedShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);
  const [hoverExpanded, setHoverExpanded] = useState(false);
  const [contentMenuOpen, setContentMenuOpen] = useState(true);

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

  const breadcrumbs = useMemo(() => buildBreadcrumbs(location.pathname), [location.pathname]);

  const sidebarExpanded = !collapsed || hoverExpanded;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background font-body text-body-md text-on-surface">
      <aside
        className={`flex h-full shrink-0 flex-col border-r border-outline-variant bg-surface-container-lowest py-md transition-all duration-200 ${
          sidebarExpanded ? "w-panel-width-side" : "w-[64px]"
        }`}
        onMouseEnter={() => collapsed && setHoverExpanded(true)}
        onMouseLeave={() => setHoverExpanded(false)}
      >
        <nav className="flex-1 space-y-1 overflow-y-auto overflow-x-hidden px-sm">
          {/* Document Types */}
          <NavLink
            to="/document-types"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Document Types"
          >
            <span className="material-symbols-outlined shrink-0">schema</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Document Types
            </span>
          </NavLink>

          {/* Content Library (Dropdown/Submenu) */}
          <div className="space-y-1">
            <button
              onClick={() => sidebarExpanded && setContentMenuOpen(!contentMenuOpen)}
              className={`w-full flex items-center justify-between rounded px-sm py-sm text-secondary hover:bg-surface-container transition-colors`}
              title="Content Library"
              type="button"
            >
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined shrink-0">library_books</span>
                <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
                  Content Library
                </span>
              </div>
              {sidebarExpanded && (
                <span className="material-symbols-outlined text-sm transition-transform duration-200">
                  {contentMenuOpen ? "expand_less" : "expand_more"}
                </span>
              )}
            </button>

            {/* Submenu Items */}
            {sidebarExpanded && contentMenuOpen && (
              <div className="pl-6 space-y-1">
                <NavLink
                  to="/content/templates"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                      isActive
                        ? "bg-surface-container font-bold text-primary"
                        : "text-secondary hover:bg-surface-container"
                    }`
                  }
                  title="Templates"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">description</span>
                  <span className="text-body-sm whitespace-nowrap">Templates</span>
                </NavLink>
                <NavLink
                  to="/content/static"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                      isActive
                        ? "bg-surface-container font-bold text-primary"
                        : "text-secondary hover:bg-surface-container"
                    }`
                  }
                  title="Static PDFs"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">picture_as_pdf</span>
                  <span className="text-body-sm whitespace-nowrap">Static PDFs</span>
                </NavLink>
                <NavLink
                  to="/content/xlsx-templates"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                      isActive
                        ? "bg-surface-container font-bold text-primary"
                        : "text-secondary hover:bg-surface-container"
                    }`
                  }
                  title="XLSX Templates"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">table</span>
                  <span className="text-body-sm whitespace-nowrap">XLSX Templates</span>
                </NavLink>
              </div>
            )}
          </div>

          {/* Document Designs */}
          <NavLink
            to="/document-designs"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Document Designs"
          >
            <span className="material-symbols-outlined shrink-0">dashboard_customize</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Document Designs
            </span>
          </NavLink>

          {/* Generation Jobs */}
          <NavLink
            to="/generation-jobs"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Generation Jobs"
          >
            <span className="material-symbols-outlined shrink-0">list_alt</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Generation Jobs
            </span>
          </NavLink>

          {/* Documents Library */}
          <NavLink
            to="/document-issuances"
            end
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Documents Library"
          >
            <span className="material-symbols-outlined shrink-0">folder_open</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Documents Library
            </span>
          </NavLink>
        </nav>

        <div className="space-y-1 border-t border-outline-variant px-sm pt-md">
          <span
            className="flex cursor-default items-center gap-3 rounded px-sm py-sm text-secondary"
            title="Support"
          >
            <span className="material-symbols-outlined shrink-0">help</span>
            <span className={`whitespace-nowrap text-body-sm ${sidebarExpanded ? "opacity-100" : "opacity-0"}`}>
              Support
            </span>
          </span>
          <span
            className="flex cursor-default items-center gap-3 rounded px-sm py-sm text-secondary"
            title="Logs"
          >
            <span className="material-symbols-outlined shrink-0">history</span>
            <span className={`whitespace-nowrap text-body-sm ${sidebarExpanded ? "opacity-100" : "opacity-0"}`}>
              Logs
            </span>
          </span>
        </div>
      </aside>

      {loading ? null : (
        <main className="flex h-screen flex-1 flex-col overflow-hidden">
          <header className="z-50 flex h-16 shrink-0 items-center justify-between border-b border-outline-variant bg-surface px-lg">
            <div className="flex items-center gap-md">
              <button
                className="rounded p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                onClick={() => setCollapsed((v) => !v)}
                title={collapsed ? "Expand menu" : "Collapse menu"}
                type="button"
              >
                <span className="material-symbols-outlined">menu</span>
              </button>
              <Link
                to="/"
                className="rounded p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                title="Home"
              >
                <span className="material-symbols-outlined">home</span>
              </Link>
              {breadcrumbs.length > 0 ? (
                <nav className="flex items-center gap-sm">
                  {breadcrumbs.map((crumb, idx) => (
                    <span key={crumb.to} className="flex items-center gap-sm">
                      {idx > 0 ? (
                        <span className="material-symbols-outlined text-sm text-secondary">chevron_right</span>
                      ) : null}
                      <Link
                        to={crumb.to}
                        className={`text-body-sm transition-colors ${
                          idx === breadcrumbs.length - 1
                            ? "font-bold text-on-surface"
                            : "text-secondary hover:text-primary"
                        }`}
                      >
                        {crumb.label}
                      </Link>
                    </span>
                  ))}
                </nav>
              ) : null}
            </div>

            <div className="flex items-center gap-md">
              <div className="relative flex items-center">
                <span className="material-symbols-outlined absolute left-3 text-body-sm text-secondary">
                  search
                </span>
                <input
                  className="w-64 rounded-full border border-outline bg-surface-container-low py-1.5 pl-10 pr-4 text-body-sm focus:border-primary focus:outline-none"
                  placeholder="Global search..."
                  type="text"
                />
              </div>
              <button
                className="rounded-full p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                title="Notifications"
                type="button"
              >
                <span className="material-symbols-outlined">notifications</span>
              </button>
              <button
                className="rounded-full p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                title="Sync status"
                type="button"
              >
                <span className="material-symbols-outlined">cloud_done</span>
              </button>
              <div className="mx-1 h-8 w-px bg-outline-variant" />
              {user ? (
                <div className="flex items-center gap-sm">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-outline bg-primary text-label-caps font-bold text-on-primary">
                    {initialsFromEmail(user.email)}
                  </div>
                  <button
                    className="rounded border border-outline-variant px-md py-xs text-label-caps text-secondary transition-colors hover:border-outline hover:text-primary"
                    type="button"
                    onClick={handleSignOut}
                  >
                    Sign out
                  </button>
                </div>
              ) : null}
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-lg">
            <div className="w-full">
              <Outlet />
            </div>
          </div>
        </main>
      )}
    </div>
  );
}
