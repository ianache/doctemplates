import { useEffect, useState } from "react";

import type { DocumentDesignPage } from "../../../lib/documentDesigns";

interface DesignPageInspectorProps {
  page: DocumentDesignPage | null;
  onSave: (
    pageId: string,
    values: { title: string | null; notes: string | null; config: Record<string, unknown> },
  ) => Promise<void>;
  readOnly?: boolean;
}

export default function DesignPageInspector({ page, onSave, readOnly = false }: DesignPageInspectorProps) {
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [configJson, setConfigJson] = useState("{}");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setTitle(page?.title ?? "");
    setNotes(page?.notes ?? "");
    setConfigJson(JSON.stringify(page?.config ?? {}, null, 2));
    setError(null);
  }, [page]);

  if (!page) {
    return (
      <aside className="rounded border border-outline-variant bg-surface-container-lowest p-md">
        <h2 className="font-headings text-[18px] font-bold text-on-surface">Inspector</h2>
        <p className="mt-xs text-sm leading-5 text-on-surface-variant">
          Select a page in the stack to review its title, notes, and configuration.
        </p>
      </aside>
    );
  }

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const parsed = JSON.parse(configJson) as Record<string, unknown>;
      await onSave(page.id, {
        title: title || null,
        notes: notes || null,
        config: parsed,
      });
    } catch (err) {
      setError(err instanceof SyntaxError ? "Config must be valid JSON." : "We couldn't save this page.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <aside className="rounded border border-outline-variant bg-surface-container-lowest p-md">
      <h2 className="font-headings text-[18px] font-bold text-on-surface">Inspector</h2>
      <p className="mt-xs text-[11px] font-bold uppercase text-secondary">
        {page.block_type === "html_template" ? "Template" : "PDF"}
      </p>

      {error ? <p className="mt-md text-sm text-error">{error}</p> : null}

      <div className="mt-md space-y-md">
        {readOnly ? (
          <>
            <div className="block">
              <span className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">Title</span>
              <div className="mt-xs w-full rounded border border-outline-variant bg-surface-container px-sm py-xs text-sm text-on-surface">
                {title || <span className="italic text-on-surface-variant">No title</span>}
              </div>
            </div>

            <div className="block">
              <span className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">Notes</span>
              <div className="mt-xs w-full rounded border border-outline-variant bg-surface-container px-sm py-xs text-sm text-on-surface whitespace-pre-wrap">
                {notes || <span className="italic text-on-surface-variant">No notes</span>}
              </div>
            </div>

            <div className="block">
              <span className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">Config</span>
              <pre className="mt-xs w-full rounded border border-outline-variant bg-surface-container px-sm py-xs font-mono text-[12px] text-on-surface overflow-x-auto whitespace-pre-wrap max-h-60">
                {configJson}
              </pre>
            </div>
          </>
        ) : (
          <>
            <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              Title
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
              />
            </label>

            <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              Notes
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                rows={4}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
              />
            </label>

            <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              Config
              <textarea
                value={configJson}
                onChange={(event) => setConfigJson(event.target.value)}
                rows={5}
                className="mt-xs w-full rounded border border-outline px-sm py-xs font-mono text-[12px] text-on-surface focus:border-primary focus:outline-none"
              />
            </label>

            <button
              type="button"
              disabled={saving}
              className="w-full rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50"
              onClick={handleSave}
            >
              Save Page
            </button>
          </>
        )}
      </div>
    </aside>
  );
}
