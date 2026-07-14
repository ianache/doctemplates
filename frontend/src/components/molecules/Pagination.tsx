import Icon from "../atoms/Icon";
import Select from "../atoms/Select";

export interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  itemName: string;
  onChangePage: (page: number) => void;
  pageSizeOptions?: number[];
  onChangePageSize?: (pageSize: number) => void;
}

const NAV_BTN =
  "w-8 h-8 flex items-center justify-center rounded border border-outline-variant bg-white text-secondary hover:bg-surface transition-colors disabled:opacity-50";
const NUM_BTN_BASE = "w-8 h-8 flex items-center justify-center rounded border text-body-sm";
const NUM_BTN_ACTIVE = "border-primary bg-primary text-on-primary font-bold";
const NUM_BTN_IDLE = "border-outline-variant bg-white text-secondary hover:bg-surface";

function buildPageList(page: number, totalPages: number): (number | "...")[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  const set = new Set<number>([1, totalPages, page - 1, page, page + 1]);
  const sorted = Array.from(set)
    .filter((p) => p >= 1 && p <= totalPages)
    .sort((a, b) => a - b);
  const result: (number | "...")[] = [];
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) result.push("...");
    result.push(p);
    prev = p;
  }
  return result;
}

export default function Pagination({
  page,
  pageSize,
  total,
  itemName,
  onChangePage,
  pageSizeOptions,
  onChangePageSize,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const startIdx = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endIdx = Math.min(page * pageSize, total);
  const pages = buildPageList(page, totalPages);
  const showPageSizeSelector = Boolean(pageSizeOptions && onChangePageSize);

  return (
    <div className="mt-auto flex flex-col gap-sm border-t border-outline-variant bg-surface-container-low p-md sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-xs sm:flex-row sm:items-center sm:gap-md">
        <p className="text-body-sm text-secondary">
          Showing <span className="font-bold text-on-surface">{startIdx}-{endIdx}</span> of {total} {itemName}
        </p>
        {showPageSizeSelector ? (
          <label className="flex items-center gap-sm text-body-sm text-secondary">
            <span>Rows per page</span>
            <Select
              className="w-auto min-w-[4.5rem] bg-white"
              value={String(pageSize)}
              onChange={(event) => onChangePageSize?.(Number(event.target.value))}
            >
              {pageSizeOptions?.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          </label>
        ) : null}
      </div>
      <div className="flex items-center gap-1">
        <button
          type="button"
          className={NAV_BTN}
          disabled={page === 1}
          onClick={() => onChangePage(page - 1)}
          aria-label="Previous page"
        >
          <Icon name="chevron_left" />
        </button>
        {pages.map((p, idx) =>
          p === "..." ? (
            <span key={`gap-${idx}`} className="w-8 h-8 flex items-center justify-center text-secondary">
              ...
            </span>
          ) : (
            <button
              key={p}
              type="button"
              className={`${NUM_BTN_BASE} ${p === page ? NUM_BTN_ACTIVE : NUM_BTN_IDLE}`}
              onClick={() => onChangePage(p)}
            >
              {p}
            </button>
          ),
        )}
        <button
          type="button"
          className={NAV_BTN}
          disabled={page === totalPages}
          onClick={() => onChangePage(page + 1)}
          aria-label="Next page"
        >
          <Icon name="chevron_right" />
        </button>
      </div>
    </div>
  );
}
