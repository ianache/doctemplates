import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../../components/molecules/PageHeader";
import DateRange from "../../components/molecules/DateRange";
import {
  listDocumentIssuances,
  type DocumentIssuanceListItem,
  type DocumentIssuanceStatus,
} from "../../lib/documentIssuances";

const STATUS_LABELS: Record<DocumentIssuanceStatus, string> = {
  queued: "Queued",
  processing: "Processing",
  success: "Success",
  failure: "Failure",
};

const STATUS_STYLES: Record<DocumentIssuanceStatus, string> = {
  queued: "bg-blue-100 text-blue-800 border-blue-200",
  processing: "bg-amber-100 text-amber-800 border-amber-200",
  success: "bg-green-100 text-green-800 border-green-200",
  failure: "bg-red-100 text-red-800 border-red-200",
};

function formatTime(value: string | null | undefined): string {
  if (!value) return "--:--:--";
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "--";
  return new Date(value).toLocaleDateString();
}

function calculateDuration(start: string | null | undefined, end: string | null | undefined): string {
  if (!start || !end) return "--";
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  if (isNaN(s) || isNaN(e)) return "--";
  const diff = (e - s) / 1000;
  return `${diff.toFixed(1)}s`;
}

function getInitials(email: string | null | undefined): string {
  if (!email) return "??";
  const parts = email.split("@")[0].split(/[._-]+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

export default function JobsMonitoringPage() {
  const [items, setItems] = useState<DocumentIssuanceListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [createdByUser, setCreatedByUser] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // Auto-polling and fetching
  useEffect(() => {
    let cancelled = false;
    let timeoutId: any = null;
    let pollCount = 0;

    const fetchJobs = () => {
      setError(null);
      // We retrieve all issuances, then filter them on client side for comprehensive stats and details
      listDocumentIssuances({})
        .then((data) => {
          if (cancelled) return;
          setItems(data);

          // Check if any job is currently in progress (queued or processing)
          const hasInProgress = data.some(
            (job) => job.status === "queued" || job.status === "processing"
          );

          if (hasInProgress) {
            pollCount++;
            // Poll every 2s for first 60 seconds (30 polls), then every 5s
            const delay = pollCount <= 30 ? 2000 : 5000;
            timeoutId = setTimeout(fetchJobs, delay);
          }
        })
        .catch((err) => {
          if (cancelled) return;
          setItems([]);
          setError(err instanceof Error ? err.message : "Failed to load generation jobs.");
        });
    };

    fetchJobs();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [refreshTrigger]);

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleResetFilters = () => {
    setSearchQuery("");
    setStatusFilter("");
    setCreatedByUser("");
    setDateFrom("");
    setDateTo("");
  };

  // Client-side filtering
  const filteredItems = useMemo(() => {
    if (!items) return [];
    return items.filter((item) => {
      // Search by Job ID or Name
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesName = item.design_name.toLowerCase().includes(query);
        const matchesId = item.id.toLowerCase().includes(query);
        if (!matchesName && !matchesId) return false;
      }

      // Status
      if (statusFilter && item.status !== statusFilter) {
        return false;
      }

      // Created By
      if (createdByUser.trim()) {
        const userQuery = createdByUser.toLowerCase();
        if (!item.generated_by_email.toLowerCase().includes(userQuery)) {
          return false;
        }
      }

      // Date Range
      if (dateFrom) {
        const itemDate = new Date(item.created_at);
        const fromDateObj = new Date(dateFrom + "T00:00:00");
        if (itemDate < fromDateObj) return false;
      }
      if (dateTo) {
        const itemDate = new Date(item.created_at);
        const toDateObj = new Date(dateTo + "T23:59:59");
        if (itemDate > toDateObj) return false;
      }

      return true;
    });
  }, [items, searchQuery, statusFilter, createdByUser, dateFrom, dateTo]);

  // Statistics calculation based on total fetched items
  const stats = useMemo(() => {
    if (!items) return { inProgress: 0, failedToday: 0, totalSuccess: 0 };
    const todayStr = new Date().toDateString();

    const inProgress = items.filter(
      (item) => item.status === "queued" || item.status === "processing"
    ).length;

    const failedToday = items.filter((item) => {
      if (item.status !== "failure") return false;
      return new Date(item.created_at).toDateString() === todayStr;
    }).length;

    const totalSuccess = items.filter((item) => item.status === "success").length;

    return { inProgress, failedToday, totalSuccess };
  }, [items]);

  // Find the selected job detail
  const selectedJob = useMemo(() => {
    if (!selectedJobId || !items) return null;
    return items.find((item) => item.id === selectedJobId) || null;
  }, [selectedJobId, items]);

  return (
    <section className="flex flex-col gap-lg">
      <PageHeader
        breadcrumbs={[{ label: "Operations" }, { label: "Generation Jobs" }]}
        title="Generation Jobs"
        actions={
          <button
            onClick={handleRefresh}
            className="flex items-center gap-xs rounded bg-primary px-lg py-sm font-bold uppercase tracking-wide text-label-caps text-on-primary hover:opacity-90 active:scale-95 transition-all"
            type="button"
          >
            <span className="material-symbols-outlined text-[18px]">refresh</span>
            Refresh
          </button>
        }
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-md">
        <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-md flex flex-col">
          <span className="text-label-caps text-secondary uppercase font-bold">In Progress</span>
          <span className="text-headline-xl font-headings text-blue-600 font-bold mt-xs">
            {items === null ? "--" : stats.inProgress}
          </span>
        </div>
        <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-md flex flex-col">
          <span className="text-label-caps text-secondary uppercase font-bold">Failed (Today)</span>
          <span className="text-headline-xl font-headings text-primary font-bold mt-xs">
            {items === null ? "--" : stats.failedToday}
          </span>
        </div>
        <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-md flex flex-col">
          <span className="text-label-caps text-secondary uppercase font-bold">Total Success</span>
          <span className="text-headline-xl font-headings text-green-700 font-bold mt-xs">
            {items === null ? "--" : stats.totalSuccess}
          </span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-end gap-md rounded-lg border border-outline-variant bg-surface-container-lowest p-md">
        <div className="min-w-[200px] flex-1">
          <label className="mb-1 block text-label-caps text-secondary">Search</label>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-secondary">
              search
            </span>
            <input
              className="w-full rounded border border-outline-variant py-2 pl-9 pr-4 text-body-md focus:border-primary focus:ring-0 bg-surface-container-low"
              placeholder="Search by Job ID or Name..."
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div className="w-48">
          <label className="mb-1 block text-label-caps text-secondary font-bold">Status</label>
          <select
            className="w-full rounded border border-outline-variant py-2 px-3 text-body-md focus:border-primary focus:ring-0 bg-surface-container-low"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
          </select>
        </div>

        <div className="w-48">
          <label className="mb-1 block text-label-caps text-secondary font-bold">Created By</label>
          <input
            className="w-full rounded border border-outline-variant py-2 px-3 text-body-md focus:border-primary focus:ring-0 bg-surface-container-low"
            placeholder="Filter user..."
            type="text"
            value={createdByUser}
            onChange={(e) => setCreatedByUser(e.target.value)}
          />
        </div>

        <div className="min-w-[260px] flex-1">
          <DateRange
            from={dateFrom}
            to={dateTo}
            onFromChange={setDateFrom}
            onToChange={setDateTo}
            fromLabel="Date From"
            toLabel="Date To"
          />
        </div>

        <button
          className="h-[42px] rounded border border-outline-variant bg-surface-container px-md py-2 font-bold uppercase tracking-wide text-label-caps text-secondary hover:bg-surface-container-high active:scale-95 transition-all"
          type="button"
          onClick={handleResetFilters}
        >
          Reset
        </button>
      </div>

      {error ? <p className="text-sm text-error">{error}</p> : null}

      {/* Main Table and Drawer Split View */}
      <div className="flex flex-col lg:flex-row gap-lg items-start">
        {/* Jobs Table Container */}
        <div className="flex-1 w-full overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container-low">
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Job ID</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Document Name</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created By</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Start Time</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Duration</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Status</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30">
                {items === null ? (
                  <tr>
                    <td colSpan={7} className="px-md py-2xl text-center text-secondary">
                      Loading generation jobs...
                    </td>
                  </tr>
                ) : filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-md py-2xl text-center text-secondary">
                      No matching generation jobs found.
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item) => {
                    const isSelected = selectedJobId === item.id;
                    const duration = calculateDuration(item.started_at, item.completed_at);

                    return (
                      <tr
                        key={item.id}
                        onClick={() => setSelectedJobId(item.id)}
                        className={`cursor-pointer transition-colors hover:bg-surface-container-low ${
                          isSelected ? "bg-surface-container" : ""
                        }`}
                      >
                        <td className="px-md py-md font-mono text-code-sm text-on-surface-variant">
                          #{item.id.slice(0, 8)}
                        </td>
                        <td className="px-md py-md">
                          <span className="font-bold text-on-surface block hover:underline">
                            {item.design_name}
                          </span>
                          <span className="text-[11px] text-on-surface-variant block">
                            Version {item.design_version_number ?? 1} · {item.design_status}
                          </span>
                        </td>
                        <td className="px-md py-md">
                          <div className="flex items-center gap-xs">
                            <div className="w-5 h-5 rounded-full bg-primary text-[10px] text-white flex items-center justify-center font-bold font-headings">
                              {getInitials(item.generated_by_email)}
                            </div>
                            <span className="text-body-sm text-on-surface">
                              {item.generated_by_email.split("@")[0]}
                            </span>
                          </div>
                        </td>
                        <td className="px-md py-md text-body-sm text-on-surface-variant">
                          {formatTime(item.started_at || item.created_at)}
                        </td>
                        <td className="px-md py-md text-body-sm text-on-surface-variant">
                          {duration}
                        </td>
                        <td className="px-md py-md">
                          <span
                            className={`inline-flex items-center gap-1 border px-xs py-0.5 rounded font-label-caps text-[10px] uppercase font-bold tracking-wide ${
                              STATUS_STYLES[item.status]
                            }`}
                          >
                            {item.status === "processing" && (
                              <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
                            )}
                            {STATUS_LABELS[item.status]}
                          </span>
                        </td>
                        <td className="px-md py-md text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-xs">
                            {item.status === "success" ? (
                              <a
                                href={item.download_url}
                                className="text-primary hover:bg-primary/5 p-1 rounded transition-colors inline-flex items-center"
                                title="Download Document"
                                download
                              >
                                <span className="material-symbols-outlined text-[20px]">download</span>
                              </a>
                            ) : (
                              <span className="text-secondary/30 p-1 cursor-not-allowed">
                                <span className="material-symbols-outlined text-[20px]">download_for_offline</span>
                              </span>
                            )}
                            <button
                              onClick={() => setSelectedJobId(item.id)}
                              className="text-on-surface-variant hover:bg-on-surface-variant/5 p-1 rounded transition-colors inline-flex items-center"
                              title="View Details"
                              type="button"
                            >
                              <span className="material-symbols-outlined text-[20px]">visibility</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {items && (
            <div className="bg-surface-container px-md py-sm flex items-center justify-between border-t border-outline-variant">
              <span className="text-body-sm text-on-surface-variant">
                Showing <span className="font-bold">{filteredItems.length}</span> of {items.length} jobs
              </span>
            </div>
          )}
        </div>

        {/* Selected Job Details Panel */}
        {selectedJob && (
          <div className="w-full lg:w-[380px] shrink-0 rounded-lg border border-outline-variant bg-surface-container-lowest p-md shadow-sm flex flex-col gap-md">
            <div className="flex justify-between items-center border-b border-outline-variant pb-xs">
              <h3 className="font-headings text-[18px] font-bold text-on-surface">Job Specification</h3>
              <button
                onClick={() => setSelectedJobId(null)}
                className="text-secondary hover:text-primary transition-colors"
                type="button"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="flex flex-col gap-sm text-body-sm">
              <div>
                <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block">Job ID</span>
                <span className="font-mono text-on-surface select-text block break-all font-semibold">
                  {selectedJob.id}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-sm">
                <div>
                  <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block">Status</span>
                  <span
                    className={`inline-flex items-center gap-1 border px-xs py-0.5 rounded font-label-caps text-[10px] uppercase font-bold tracking-wide mt-1 ${
                      STATUS_STYLES[selectedJob.status]
                    }`}
                  >
                    {STATUS_LABELS[selectedJob.status]}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block">Retries</span>
                  <span className="font-semibold text-on-surface mt-1 block">
                    {selectedJob.retry_count ?? 0} attempts
                  </span>
                </div>
              </div>

              <div>
                <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block">Document Template</span>
                <span className="font-bold text-primary block mt-0.5">
                  {selectedJob.design_name}
                </span>
                <span className="text-[11px] text-on-surface-variant block">
                  Version {selectedJob.design_version_number ?? 1} · {selectedJob.design_status}
                </span>
              </div>

              <div>
                <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block">Triggered By</span>
                <span className="text-on-surface block font-semibold mt-0.5">{selectedJob.generated_by_email}</span>
              </div>

              <div className="border-t border-outline-variant/30 pt-xs space-y-xs">
                <div>
                  <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block">Created At</span>
                  <span className="text-on-surface-variant block">{formatDate(selectedJob.created_at)} {formatTime(selectedJob.created_at)}</span>
                </div>
                <div>
                  <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block">Started Processing</span>
                  <span className="text-on-surface-variant block">{formatDate(selectedJob.started_at)} {formatTime(selectedJob.started_at)}</span>
                </div>
                <div>
                  <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block">Completed At</span>
                  <span className="text-on-surface-variant block">{formatDate(selectedJob.completed_at)} {formatTime(selectedJob.completed_at)}</span>
                </div>
                <div>
                  <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block">Execution Duration</span>
                  <span className="text-on-surface font-semibold block">{calculateDuration(selectedJob.started_at, selectedJob.completed_at)}</span>
                </div>
              </div>

              {selectedJob.status === "failure" && selectedJob.error_message && (
                <div className="rounded border border-error-container bg-error-container/40 p-sm text-error">
                  <span className="font-bold text-xs uppercase tracking-wider block mb-1">Error Message</span>
                  <p className="font-mono text-[11px] leading-4 break-words whitespace-pre-wrap select-text">
                    {selectedJob.error_message}
                  </p>
                </div>
              )}

              <div className="border-t border-outline-variant/30 pt-xs">
                <span className="text-[11px] text-secondary font-bold uppercase tracking-wider block mb-1">Input Data</span>
                <pre className="rounded bg-surface-container-low border border-outline-variant/40 p-sm font-mono text-[10px] max-h-48 overflow-y-auto select-text">
                  {JSON.stringify(selectedJob.input_data, null, 2)}
                </pre>
              </div>

              <div className="flex gap-sm border-t border-outline-variant/30 pt-md">
                {selectedJob.status === "success" && (
                  <a
                    href={selectedJob.download_url}
                    className="flex-1 rounded bg-primary py-sm text-center font-bold text-label-caps text-on-primary uppercase hover:opacity-90 active:scale-95 transition-all"
                    download
                  >
                    Download PDF
                  </a>
                )}
                <Link
                  to={`/document-issuances/${selectedJob.id}`}
                  className="flex-grow rounded border border-outline-variant bg-surface-container py-sm text-center font-bold text-label-caps text-secondary uppercase hover:bg-surface-container-high active:scale-95 transition-all"
                >
                  View Details & Audit
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* System Status Footer */}
      <footer className="bg-inverse-surface text-surface text-body-sm px-lg py-2 flex justify-between items-center rounded-lg mt-auto shadow-sm">
        <div className="flex items-center gap-md">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-green-400 rounded-full" />
            Queue Engine: Active (Celery + Redis)
          </span>
          <span className="text-secondary/40 select-none">|</span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-green-400 rounded-full" />
            DB Connection: Stable
          </span>
        </div>
        <div>
          <span className="text-secondary/60 uppercase text-[10px] font-bold tracking-widest">
            Version 2.0.0-stable
          </span>
        </div>
      </footer>
    </section>
  );
}
