import type { ReactNode } from "react";

import { cn } from "../../lib/cn";
import Pagination from "../molecules/Pagination";
import TableHeader from "../molecules/TableHeader";

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T, index: number) => ReactNode;
  className?: string;
}

export interface PagedTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string;
  page: number;
  pageSize: number;
  total: number;
  itemName?: string;
  onChangePage: (page: number) => void;
  pageSizeOptions?: number[];
  onChangePageSize?: (pageSize: number) => void;
  emptyState?: ReactNode;
  onRowClick?: (row: T) => void;
  selectedRowId?: string | null;
}

function PagedTable<T>({
  columns,
  rows,
  rowKey,
  page,
  pageSize,
  total,
  itemName = "items",
  onChangePage,
  pageSizeOptions,
  onChangePageSize,
  emptyState,
  onRowClick,
  selectedRowId,
}: PagedTableProps<T>) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
      <table className="w-full border-collapse text-left">
        <TableHeader columns={columns} />
        <tbody className="divide-y divide-outline-variant">
          {rows.map((row, idx) => {
            const isSelected = selectedRowId && rowKey(row, idx) === selectedRowId;
            return (
              <tr
                key={rowKey(row, idx)}
                onClick={() => onRowClick?.(row)}
                className={cn(
                  "transition-colors hover:bg-surface",
                  onRowClick ? "cursor-pointer" : "",
                  isSelected ? "bg-surface-container" : ""
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className={cn("px-md py-md text-on-surface", col.className)}>
                    {col.render(row, idx)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      {rows.length === 0 && emptyState ? emptyState : null}
      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        itemName={itemName}
        onChangePage={onChangePage}
        pageSizeOptions={pageSizeOptions}
        onChangePageSize={onChangePageSize}
      />
    </div>
  );
}

export default PagedTable;
