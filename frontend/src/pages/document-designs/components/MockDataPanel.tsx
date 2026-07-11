import type { ChangeEvent } from "react";

interface MockDataPanelProps {
  value: string;
  onChange: (value: string) => void;
  onReset: () => void;
  onPreview: () => void;
  isValidJson: boolean;
  parseError: string | null;
  loadingPreview?: boolean;
}

export function MockDataPanel({
  value,
  onChange,
  onReset,
  onPreview,
  isValidJson,
  parseError,
  loadingPreview = false,
}: MockDataPanelProps) {
  return (
    <aside className="rounded border border-outline-variant bg-surface-container-lowest p-md">
      <h2 className="font-headings text-[18px] font-bold text-on-surface">Mock Data Preview</h2>
      <p className="mt-xs text-sm leading-5 text-on-surface-variant">
        Configure sample values matching your Document Type schema. Values are passed directly to template rendering.
      </p>

      {parseError ? (
        <div className="mt-md text-xs text-error bg-error/5 border border-error/20 p-xs rounded font-mono">
          {parseError}
        </div>
      ) : null}

      <div className="mt-md space-y-md">
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          Mock JSON Payload
          <textarea
            value={value}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => onChange(e.target.value)}
            rows={15}
            className="mt-xs w-full rounded border border-outline px-sm py-xs font-mono text-[12px] text-on-surface focus:border-primary focus:outline-none bg-surface-container-low"
            placeholder="{}"
          />
        </label>

        <div className="flex gap-sm">
          <button
            type="button"
            className="flex-1 rounded border border-outline px-md py-xs text-sm font-bold text-on-surface hover:bg-surface-container-low"
            onClick={onReset}
          >
            Reset
          </button>
          <button
            type="button"
            disabled={!isValidJson || loadingPreview}
            className="flex-1 rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50"
            onClick={onPreview}
          >
            {loadingPreview ? "Loading..." : "Preview PDF"}
          </button>
        </div>
      </div>
    </aside>
  );
}
