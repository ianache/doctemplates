import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getHtmlTemplate, type HtmlTemplateDetail as HtmlTemplateDetailType } from "../../lib/content";

export default function HtmlTemplateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [template, setTemplate] = useState<HtmlTemplateDetailType | null | undefined>(undefined);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getHtmlTemplate(id).then((data) => {
      if (!cancelled) setTemplate(data);
    });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (template === undefined) return null;

  if (template === null) {
    return (
      <div className="mt-xl text-center">
        <h2 className="font-headings text-[24px] font-bold text-on-surface">Content item not found.</h2>
        <p className="mt-xs text-sm text-on-surface-variant">
          Return to the library to see all templates and PDFs.
        </p>
        <Link
          to="/content"
          className="mt-lg inline-block rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
        >
          Back to Content Library
        </Link>
      </div>
    );
  }

  return (
    <section className="rounded border border-outline-variant bg-surface-container-lowest p-lg">
      <div className="flex flex-wrap items-start justify-between gap-md">
        <div>
          <h2 className="font-headings text-[18px] font-bold text-on-surface">{template.name}</h2>
          <p className="mt-xs text-sm text-on-surface-variant">{template.document_type_name}</p>
        </div>
        <Link
          to="/content"
          className="rounded border border-outline-variant px-md py-xs text-sm font-bold text-on-surface hover:border-outline"
        >
          Back to Library
        </Link>
      </div>

      <dl className="mt-md grid gap-sm text-sm">
        <div className="flex justify-between border-b border-outline-variant/40 pb-xs">
          <dt className="text-on-surface-variant">Created By</dt>
          <dd className="text-on-surface">{template.created_by_email}</dd>
        </div>
        <div className="flex justify-between border-b border-outline-variant/40 pb-xs">
          <dt className="text-on-surface-variant">Created At</dt>
          <dd className="text-on-surface">{new Date(template.created_at).toLocaleString()}</dd>
        </div>
        <div className="flex justify-between border-b border-outline-variant/40 pb-xs">
          <dt className="text-on-surface-variant">Tokens</dt>
          <dd className="text-on-surface">{template.token_names.length}</dd>
        </div>
      </dl>

      <div className="mt-lg">
        <h3 className="text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">Token Names</h3>
        <div className="mt-xs flex flex-wrap gap-xs">
          {template.token_names.map((token) => (
            <code key={token} className="rounded bg-surface-container px-2 py-0.5 text-[12px] text-on-surface">
              {token}
            </code>
          ))}
        </div>
      </div>

      <div className="mt-lg">
        <h3 className="text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">HTML</h3>
        <pre className="mt-xs overflow-x-auto rounded border border-outline-variant bg-surface-container p-md text-[12px] leading-5 text-on-surface">
          <code>{template.html}</code>
        </pre>
      </div>
    </section>
  );
}
