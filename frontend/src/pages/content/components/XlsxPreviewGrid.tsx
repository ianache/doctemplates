import type { XlsxPreviewResponse } from "../../../lib/xlsxTemplates";

function columnName(index: number): string {
  let value = "";
  let current = index;
  while (current > 0) {
    const remainder = (current - 1) % 26;
    value = String.fromCharCode(65 + remainder) + value;
    current = Math.floor((current - 1) / 26);
  }
  return value;
}

export function XlsxPreviewGrid({ preview }: { preview: XlsxPreviewResponse }) {
  const sheet = preview.sheets[0];
  if (!sheet) {
    return <p className="text-sm text-on-surface-variant">No preview available.</p>;
  }

  const byAddress = new Map(sheet.cells.map((cell) => [cell.address, cell]));
  const columns = Array.from({ length: Math.min(sheet.max_column, 12) }, (_, index) => index + 1);
  const rows = Array.from({ length: Math.min(sheet.max_row, 40) }, (_, index) => index + 1);

  return (
    <div className="overflow-auto rounded border border-outline-variant bg-surface-container-lowest">
      <table className="min-w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="h-8 w-10 border border-outline-variant bg-surface-container-low" />
            {columns.map((column) => (
              <th
                key={column}
                className="h-8 min-w-24 border border-outline-variant bg-surface-container-low px-2 text-secondary"
              >
                {columnName(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row}>
              <th className="h-8 border border-outline-variant bg-surface-container-low px-2 text-secondary">
                {row}
              </th>
              {columns.map((column) => {
                const address = `${columnName(column)}${row}`;
                const cell = byAddress.get(address);
                return (
                  <td
                    key={column}
                    className="h-8 min-w-24 border border-outline-variant px-2 align-top text-on-surface"
                  >
                    {cell?.value == null ? "" : String(cell.value)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
