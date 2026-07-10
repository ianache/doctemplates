import { cn } from "../../lib/cn";

export interface DateRangeProps {
  from: string;
  to: string;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
  fromLabel?: string;
  toLabel?: string;
  className?: string;
}

const INPUT_CLASS =
  "w-full rounded border border-outline-variant py-2 pl-3 pr-3 text-body-md focus:border-primary focus:ring-0";

export default function DateRange({
  from,
  to,
  onFromChange,
  onToChange,
  fromLabel = "Date From",
  toLabel = "Date To",
  className,
}: DateRangeProps) {
  return (
    <div className={cn("flex items-end gap-sm", className)}>
      <label className="block flex-1">
        <span className="mb-1 block text-label-caps text-secondary">{fromLabel}</span>
        <input
          className={INPUT_CLASS}
          type="date"
          value={from}
          max={to || undefined}
          onChange={(e) => onFromChange(e.target.value)}
        />
      </label>
      <span className="material-symbols-outlined pb-2 text-secondary">arrow_range</span>
      <label className="block flex-1">
        <span className="mb-1 block text-label-caps text-secondary">{toLabel}</span>
        <input
          className={INPUT_CLASS}
          type="date"
          value={to}
          min={from || undefined}
          onChange={(e) => onToChange(e.target.value)}
        />
      </label>
    </div>
  );
}
