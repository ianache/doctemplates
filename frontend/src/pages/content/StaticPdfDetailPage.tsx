import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { API_BASE_URL } from "../../lib/api";
import { getStaticPdfAsset, type StaticPdfAssetDetail as StaticPdfAssetDetailType } from "../../lib/content";

export default function StaticPdfDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [asset, setAsset] = useState<StaticPdfAssetDetailType | null | undefined>(undefined);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getStaticPdfAsset(id).then((data) => {
      if (!cancelled) setAsset(data);
    });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (asset === undefined) return null;

  if (asset === null) {
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

  const downloadHref = `${API_BASE_URL}${asset.download_url}`;

  return (
    <section className="rounded border border-outline-variant bg-surface-container-lowest p-lg">
      <div className="flex flex-wrap items-start justify-between gap-md">
        <div>
          <h2 className="font-headings text-[18px] font-bold text-on-surface">{asset.filename}</h2>
          <p className="mt-xs text-sm text-on-surface-variant">Static PDF asset</p>
        </div>
        <a
          href={downloadHref}
          className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90"
        >
          Download PDF
        </a>
      </div>

      <dl className="mt-md grid gap-sm text-sm">
        <div className="flex justify-between border-b border-outline-variant/40 pb-xs">
          <dt className="text-on-surface-variant">Created By</dt>
          <dd className="text-on-surface">{asset.created_by_email}</dd>
        </div>
        <div className="flex justify-between border-b border-outline-variant/40 pb-xs">
          <dt className="text-on-surface-variant">Created At</dt>
          <dd className="text-on-surface">{new Date(asset.created_at).toLocaleString()}</dd>
        </div>
        <div className="flex justify-between border-b border-outline-variant/40 pb-xs">
          <dt className="text-on-surface-variant">Pages</dt>
          <dd className="text-on-surface">{asset.page_count}</dd>
        </div>
        <div className="flex justify-between border-b border-outline-variant/40 pb-xs">
          <dt className="text-on-surface-variant">Page Range</dt>
          <dd className="text-on-surface">
            {asset.page_start && asset.page_end ? `${asset.page_start}-${asset.page_end}` : "Full file"}
          </dd>
        </div>
        <div className="flex justify-between border-b border-outline-variant/40 pb-xs">
          <dt className="text-on-surface-variant">Storage Path</dt>
          <dd className="max-w-[70%] truncate font-mono text-[12px] text-on-surface">{asset.stored_path}</dd>
        </div>
      </dl>

      <div className="mt-lg">
        <h3 className="text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">Download URL</h3>
        <code className="mt-xs block rounded border border-outline-variant bg-surface-container px-md py-sm text-[12px] text-on-surface">
          {asset.download_url}
        </code>
      </div>
    </section>
  );
}
