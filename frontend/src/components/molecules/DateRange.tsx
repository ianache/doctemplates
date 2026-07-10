import { useEffect, useMemo, useRef, useState } from "react";

import Icon from "../atoms/Icon";
import { cn } from "../../lib/cn";

export interface DateRangeProps {
  from: string;
  to: string;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
  fromLabel?: string;
  toLabel?: string;
  maxDays?: number;
  className?: string;
}

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function parseISODate(s: string): Date | null {
  if (!s) return null;
  const parts = s.split("-");
  if (parts.length !== 3) return null;
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  return Number.isNaN(d.getTime()) ? null : d;
}

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function daysBetween(a: Date, b: Date): number {
  const ms = startOfDay(b).getTime() - startOfDay(a).getTime();
  return Math.round(ms / 86400000);
}

function isBetween(d: Date, a: Date, b: Date): boolean {
  const t = startOfDay(d).getTime();
  const ta = startOfDay(a).getTime();
  const tb = startOfDay(b).getTime();
  const lo = Math.min(ta, tb);
  const hi = Math.max(ta, tb);
  return t > lo && t < hi;
}

function buildMonthGrid(year: number, month: number): (Date | null)[] {
  const first = new Date(year, month, 1);
  const startWeekday = first.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (Date | null)[] = [];
  for (let i = 0; i < startWeekday; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

function formatDisplay(s: string): string {
  const d = parseISODate(s);
  if (!d) return "";
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

export default function DateRange({
  from,
  to,
  onFromChange,
  onToChange,
  fromLabel = "Date From",
  toLabel = "Date To",
  maxDays = 7,
  className,
}: DateRangeProps) {
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(() => {
    const d = parseISODate(from) ?? new Date();
    return d.getFullYear();
  });
  const [viewMonth, setViewMonth] = useState(() => {
    const d = parseISODate(from) ?? new Date();
    return d.getMonth();
  });
  const [hoverDate, setHoverDate] = useState<Date | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const fromDate = useMemo(() => parseISODate(from), [from]);
  const toDate = useMemo(() => parseISODate(to), [to]);

  const cells = useMemo(() => buildMonthGrid(viewYear, viewMonth), [viewYear, viewMonth]);

  const pendingFrom = fromDate && !toDate ? fromDate : null;

  const effectiveTo = hoverDate && pendingFrom && daysBetween(pendingFrom, hoverDate) >= 0 ? hoverDate : toDate;

  const rangeStart = pendingFrom ?? fromDate;
  const rangeEnd = effectiveTo;

  const goPrevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
  };

  const goNextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
  };

  const handleDayClick = (d: Date) => {
    if (!pendingFrom) {
      onFromChange(toISODate(d));
      onToChange("");
      return;
    }
    const diff = daysBetween(pendingFrom, d);
    if (diff < 0) {
      onFromChange(toISODate(d));
      onToChange("");
      return;
    }
    if (maxDays > 0 && diff >= maxDays) {
      const capped = new Date(pendingFrom);
      capped.setDate(capped.getDate() + maxDays - 1);
      onToChange(toISODate(capped));
      setOpen(false);
      return;
    }
    onToChange(toISODate(d));
    setOpen(false);
  };

  const isDisabled = (d: Date): boolean => {
    if (!pendingFrom) return false;
    const diff = daysBetween(pendingFrom, d);
    if (diff < 0) return false;
    return maxDays > 0 && diff >= maxDays;
  };

  const dayClass = (d: Date | null): string => {
    if (!d) return "text-transparent";
    const base = "h-8 w-8 flex items-center justify-center rounded text-body-sm transition-colors cursor-pointer select-none";
    if (isDisabled(d)) return cn(base, "text-secondary opacity-30 cursor-not-allowed");
    if (rangeStart && sameDay(d, rangeStart)) return cn(base, "bg-primary text-on-primary font-bold");
    if (rangeEnd && sameDay(d, rangeEnd)) return cn(base, "bg-primary text-on-primary font-bold");
    if (rangeStart && rangeEnd && isBetween(d, rangeStart, rangeEnd)) return cn(base, "bg-primary/20 text-primary");
    return cn(base, "text-on-surface hover:bg-surface-container-high");
  };

  const displayText = from && to
    ? `${formatDisplay(from)} — ${formatDisplay(to)}`
    : from
      ? `${formatDisplay(from)} — ...`
      : "Select date range";

  const handleClear = () => {
    onFromChange("");
    onToChange("");
  };

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <div className="flex items-end gap-sm">
        <label className="block flex-1">
          <span className="mb-1 block text-label-caps text-secondary">{fromLabel}</span>
          <button
            type="button"
            className="w-full rounded border border-outline-variant bg-surface-container-lowest py-2 pl-9 pr-3 text-left text-body-md focus:border-primary focus:ring-0"
            onClick={() => setOpen((v) => !v)}
          >
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-secondary">
              calendar_month
            </span>
            {displayText}
          </button>
        </label>
        {from || to ? (
          <button
            type="button"
            className="flex h-[42px] items-center justify-center rounded border border-outline-variant bg-surface-container px-sm text-secondary hover:bg-surface-container-high"
            onClick={handleClear}
            aria-label="Clear dates"
          >
            <Icon name="close" className="text-sm" />
          </button>
        ) : null}
      </div>
      <span className="mb-1 mt-1 block text-label-caps text-secondary">{toLabel}</span>
      {open ? (
        <div className="absolute z-50 mt-xs w-[320px] rounded-lg border border-outline-variant bg-surface-container-lowest p-md shadow-lg">
          <div className="mb-md flex items-center justify-between">
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded text-secondary hover:bg-surface-container"
              onClick={goPrevMonth}
              aria-label="Previous month"
            >
              <Icon name="chevron_left" className="text-sm" />
            </button>
            <span className="font-headings text-headline-md font-bold text-on-surface">
              {MONTHS[viewMonth]} {viewYear}
            </span>
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded text-secondary hover:bg-surface-container"
              onClick={goNextMonth}
              aria-label="Next month"
            >
              <Icon name="chevron_right" className="text-sm" />
            </button>
          </div>
          <div className="mb-xs grid grid-cols-7">
            {WEEKDAYS.map((wd, i) => (
              <div key={i} className="flex h-8 items-center justify-center text-label-caps text-secondary">
                {wd}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {cells.map((d, i) => (
              <div
                key={i}
                className="flex justify-center"
                onMouseEnter={() => d && setHoverDate(d)}
                onMouseLeave={() => setHoverDate(null)}
              >
                {d ? (
                  <button
                    type="button"
                    className={dayClass(d)}
                    disabled={isDisabled(d)}
                    onClick={() => handleDayClick(d)}
                  >
                    {d.getDate()}
                  </button>
                ) : (
                  <span className="h-8 w-8" />
                )}
              </div>
            ))}
          </div>
          {maxDays > 0 ? (
            <p className="mt-md text-body-sm text-secondary">
              Max {maxDays} days
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
