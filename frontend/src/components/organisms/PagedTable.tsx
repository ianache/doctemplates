import type { ReactNode } from "react";

import { cn } from "../atoms/Icon";
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
  emptyState?: ReactNode;
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
  emptyState,
}: PagedTableProps<T>) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
      <table className="w-full border-collapse text-left">
        <TableHeader columns={columns} />
        <tbody className="divide-y divide-outline-variant">
          {rows.map((row, idx) => (
            <tr key={rowKey(row, idx)} className="transition-colors hover:bg-surface">
              {columns.map((col) => (
                <td key={col.key} className={cn("px-md py-md text-on-surface", col.className)}>
                  {col.render(row, idx)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && emptyState ? emptyState : null}
      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        itemName={itemName}
        onChangePage={onChangePage}
      />
    </div>
  );
}

export default PagedTable;
