import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  listDocumentDesignVersions,
  getDocumentDesign,
  type DocumentDesignListItem,
  type DocumentDesignDetail,
} from "../../lib/documentDesigns";

export default function VersionHistoryPage() {
  const { id } = useParams<{ id: string }>();
  const [versions, setVersions] = useState<DocumentDesignListItem[] | null>(null);
  const [design, setDesign] = useState<DocumentDesignDetail | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    // Load design details for header name
    getDocumentDesign(id)
      .then((data) => {
        if (!cancelled) setDesign(data);
      })
      .catch(() => {});

    // Load version history
    listDocumentDesignVersions(id)
      .then((data) => {
        if (!cancelled) setVersions(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <section className="py-xl">
        <p className="text-sm text-error">We couldn't load version history. Try again.</p>
      </section>
    );
  }

  if (versions === null || design === null) {
    return null;
  }

  return (
    <section>
      <div className="flex flex-wrap items-center gap-sm text-sm text-on-surface-variant mb-md">
        <span className="material-symbols-outlined text-[16px]">arrow_back</span>
        <Link to={`/document-designs/${design.id}`} className="hover:underline font-bold text-primary">
          Back to Design
        </Link>
      </div>

      <div className="flex flex-wrap items-end justify-between gap-md">
        <div>
          <h1 className="font-headings text-[24px] font-bold leading-[32px] text-on-surface">
            Version History
          </h1>
          <p className="mt-xs text-sm leading-5 text-on-surface-variant max-w-2xl">
            Every saved edit to this design is preserved here. The current version is what generation and preview use.
          </p>
        </div>
      </div>

      <div className="mt-xl">
        {versions.length === 0 ? (
          <div className="rounded border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
            <h2 className="font-headings text-[18px] font-bold text-on-surface">No versions found.</h2>
            <p className="mt-xs text-sm text-on-surface-variant">This design has no recorded versions yet.</p>
          </div>
        ) : (
          <div className="rounded border border-outline-variant bg-surface-container-lowest overflow-hidden">
            <table className="w-full">
              <thead className="bg-surface-container border-b border-outline-variant">
                <tr>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Version
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    State
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Status
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Created By
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Created At
                  </th>
                  <th className="px-md py-sm text-right text-[11px] font-bold uppercase text-secondary">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {versions.map((v) => {
                  // State determination
                  let stateLabel = "Superseded";
                  let stateClass = "text-on-surface-variant";
                  if (v.status === "active") {
                    stateLabel = "Current";
                    stateClass = "text-primary";
                  } else if (v.status === "draft") {
                    stateLabel = "Draft";
                    stateClass = "text-primary";
                  }

                  return (
                    <tr key={v.id} className="hover:bg-surface-container-lowest">
                      <td className="px-md py-sm text-sm font-bold text-on-surface">
                        {v.version_number !== null ? `Version ${v.version_number}` : "Draft"}
                      </td>
                      <td className="px-md py-sm text-sm">
                        <span className={`inline-block rounded bg-surface-container px-sm py-xs text-[11px] font-bold uppercase ${stateClass}`}>
                          {stateLabel}
                        </span>
                      </td>
                      <td className="px-md py-sm text-sm text-on-surface uppercase">
                        {v.status}
                      </td>
                      <td className="px-md py-sm text-sm text-on-surface">
                        {v.created_by_email}
                      </td>
                      <td className="px-md py-sm text-sm text-on-surface">
                        {new Date(v.created_at).toLocaleString()}
                      </td>
                      <td className="px-md py-sm text-sm text-right">
                        <Link
                          to={`/document-designs/${v.id}`}
                          className="font-bold text-primary hover:underline"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
