import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { type DocumentTypeDetail, getDocumentType } from "../../lib/documentTypes";

export default function DocumentTypeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [documentType, setDocumentType] = useState<DocumentTypeDetail | null | undefined>(
    undefined,
  );

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getDocumentType(id).then((data) => {
      if (!cancelled) setDocumentType(data);
    });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (documentType === undefined) return null;

  if (documentType === null) {
    return (
      <div className="text-center">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
          Document type not found.
        </h1>
        <p className="mt-sm text-sm leading-5 text-on-surface-variant">
          It may have been removed. Return to the list to see all document types.
        </p>
        <Link
          to="/document-types"
          className="mt-lg inline-block rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
        >
          Back to Document Types
        </Link>
      </div>
    );
  }

  return (
    <section>
      <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
        {documentType.name}
      </h1>
      <p className="mt-xs text-sm leading-5 text-on-surface-variant">{documentType.description}</p>

      <div className="mt-md flex justify-between border-b border-outline-variant/30 pb-xs text-sm">
        <span className="text-on-surface-variant">Created By</span>
        <span className="text-on-surface">{documentType.created_by_email}</span>
      </div>
      <div className="flex justify-between border-b border-outline-variant/30 pb-xs pt-xs text-sm">
        <span className="text-on-surface-variant">Created At</span>
        <span className="text-on-surface">
          {new Date(documentType.created_at).toLocaleDateString()}
        </span>
      </div>

      <div className="mt-xl rounded-lg border border-outline-variant bg-surface-container-lowest">
        {documentType.fields.map((field, index) => (
          <div
            key={field.id}
            className={`flex items-center gap-md px-md py-sm ${
              index > 0 ? "border-t border-outline-variant" : ""
            }`}
          >
            <code className="font-mono text-[12px] leading-[18px] text-on-surface">
              {field.name}
            </code>
            <span className="rounded bg-surface-container px-2 py-0.5 text-[11px] font-bold uppercase text-on-surface-variant">
              {field.type}
            </span>
            <span className="text-sm text-on-surface-variant">{field.description}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
