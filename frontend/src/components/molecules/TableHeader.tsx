import type { Column } from "../organisms/PagedTable";

interface TableHeaderProps<T> {
  columns: Column<T>[];
}

export default function TableHeader<T>({ columns }: TableHeaderProps<T>) {
  return (
    <thead>
      <tr className="border-b border-outline-variant bg-surface-container-low">
        {columns.map((col) => (
          <th key={col.key} className="px-md py-sm font-bold uppercase text-label-caps text-secondary">
            {col.header}
          </th>
        ))}
      </tr>
    </thead>
  );
}
