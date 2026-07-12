import { CSS } from "@dnd-kit/utilities";
import { useSortable } from "@dnd-kit/sortable";

import type { DocumentDesignPage } from "../../../../lib/documentDesigns";

interface DesignPageCardProps {
  page: DocumentDesignPage;
  selected: boolean;
  onSelect: (pageId: string) => void;
  onRemove: (page: DocumentDesignPage) => void;
  readOnly?: boolean;
}

function labelFor(page: DocumentDesignPage) {
  if (page.title) return page.title;
  if (page.block_type === "html_template") return String(page.snapshot.name ?? "HTML template");
  return String(page.snapshot.filename ?? "Static PDF");
}

function metadataFor(page: DocumentDesignPage) {
  if (page.block_type === "html_template") {
    const tokens = Array.isArray(page.snapshot.token_names) ? page.snapshot.token_names : [];
    return tokens.length ? `${tokens.length} token${tokens.length === 1 ? "" : "s"}` : "No tokens";
  }

  const pageCount = Number(page.snapshot.page_count ?? 0);
  const pageStart = page.snapshot.page_start;
  const pageEnd = page.snapshot.page_end;
  const range = pageStart && pageEnd ? ` · pages ${pageStart}-${pageEnd}` : "";
  return `${pageCount} page${pageCount === 1 ? "" : "s"}${range}`;
}

export default function DesignPageCard({
  page,
  selected,
  onSelect,
  onRemove,
  readOnly = false,
}: DesignPageCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: page.id,
    disabled: readOnly,
  });

  const style = readOnly
    ? undefined
    : {
        transform: CSS.Transform.toString(transform),
        transition,
      };

  return (
    <div
      ref={readOnly ? undefined : setNodeRef}
      style={style}
      className={`rounded border bg-surface-container-lowest px-md py-sm ${
        selected ? "border-primary" : "border-outline-variant"
      } ${!readOnly && isDragging ? "opacity-70 shadow-lg" : ""}`}
    >
      <div className="flex items-start gap-md">
        {!readOnly && (
          <button
            type="button"
            aria-label="Drag page"
            className="mt-xs cursor-grab text-secondary active:cursor-grabbing"
            {...attributes}
            {...listeners}
          >
            <span className="material-symbols-outlined text-[20px]">drag_indicator</span>
          </button>
        )}

        <button type="button" className="min-w-0 flex-1 text-left" onClick={() => onSelect(page.id)}>
          <p className="text-[11px] font-bold uppercase text-secondary">
            Page {page.position + 1} · {page.block_type === "html_template" ? "Template" : "PDF"}
          </p>
          <h2 className="mt-xs truncate font-headings text-[18px] font-bold text-on-surface">
            {labelFor(page)}
          </h2>
          <p className="mt-xs truncate text-sm text-on-surface-variant">{metadataFor(page)}</p>
        </button>

        {!readOnly && (
          <button
            type="button"
            aria-label="Remove page"
            className="rounded border border-outline-variant px-xs py-xs text-error hover:border-error"
            onClick={() => onRemove(page)}
          >
            <span className="material-symbols-outlined text-[18px]">delete</span>
          </button>
        )}
      </div>
    </div>
  );
}
