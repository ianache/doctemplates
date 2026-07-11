import type { ReactNode } from "react";

export interface Breadcrumb {
  label: string;
  to?: string;
}

interface PageHeaderProps {
  breadcrumbs: Breadcrumb[];
  title: string;
  actions?: ReactNode;
}

export default function PageHeader({ breadcrumbs, title, actions }: PageHeaderProps) {
  return (
    <div className="mb-lg">
      <div className="mb-2 flex items-center gap-2 text-label-caps text-secondary">
        {breadcrumbs.map((bc, idx) => (
          <span key={idx} className="flex items-center gap-2">
            {bc.to ? (
              <span className="text-secondary">{bc.label}</span>
            ) : (
              <span className="font-bold text-primary">{bc.label}</span>
            )}
            {idx < breadcrumbs.length - 1 && (
              <span className="material-symbols-outlined text-xs">chevron_right</span>
            )}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap items-end justify-between gap-md">
        <h2 className="font-headings text-headline-xl font-bold text-on-surface">{title}</h2>
        {actions ? <div className="flex items-center gap-sm">{actions}</div> : null}
      </div>
    </div>
  );
}
