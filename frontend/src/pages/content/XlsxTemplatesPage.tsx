import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import { listXlsxTemplates, type XlsxTemplateDetail } from "../../lib/xlsxTemplates";

export default function XlsxTemplatesPage() {
  const [items, setItems] = useState<XlsxTemplateDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listXlsxTemplates()
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "We couldn't load XLSX templates.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Content Library" }, { label: "XLSX Templates" }]}
        title="XLSX Templates"
        actions={
          <Link to="/content/xlsx-templates/upload" className="rounded bg-primary px-md py-xs text-sm font-bold text-on-primary">
            Upload XLSX
          </Link>
        }
      />
      {error ? <p className="mb-md text-sm text-error">{error}</p> : null}
      <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-outline-variant bg-surface-container-low">
              <th className="px-md py-sm text-label-caps text-secondary">Name</th>
              <th className="px-md py-sm text-label-caps text-secondary">Document Type</th>
              <th className="px-md py-sm text-label-caps text-secondary">Tokens</th>
              <th className="px-md py-sm text-label-caps text-secondary">Warnings</th>
              <th className="px-md py-sm text-label-caps text-secondary">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant">
            {(items ?? []).map((item) => (
              <tr key={item.id} className="hover:bg-surface">
                <td className="px-md py-md">
                  <Link className="font-bold text-primary hover:underline" to={`/content/xlsx-templates/${item.id}`}>
                    {item.name}
                  </Link>
                </td>
                <td className="px-md py-md">{item.document_type_name}</td>
                <td className="px-md py-md">{item.detected_tokens.length}</td>
                <td className="px-md py-md">{item.validation_warnings.length}</td>
                <td className="px-md py-md">{new Date(item.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
