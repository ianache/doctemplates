import { useEffect, useMemo, useRef, useState } from "react";

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

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
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
  while (cells.length < 42) cells.push(null);
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
  fromLabel = "Date Range",
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

  const getDayClasses = (d: Date): string => {
    const isStart = rangeStart && sameDay(d, rangeStart);
    const isEnd = rangeEnd && sameDay(d, rangeEnd);
    const isMid = rangeStart && rangeEnd && isBetween(d, rangeStart, rangeEnd);
    const disabled = isDisabled(d);

    if (disabled) return "text-secondary opacity-30 cursor-not-allowed";
    if (isStart || isEnd) return "bg-primary text-on-primary font-bold";
    if (isMid) return "bg-primary/20 text-primary";
    return "text-on-surface hover:bg-surface-container-high";
  };

  const displayText = from && to
    ? `${formatDisplay(from)}  —  ${formatDisplay(to)}`
    : from
      ? `${formatDisplay(from)}  —  Select end...`
      : "Select date range";

  const handleClear = () => {
    onFromChange("");
    onToChange("");
  };

  const CELL = "h-9 flex items-center justify-center";
  const DAY_BTN = "h-8 w-8 flex items-center justify-center rounded text-body-sm transition-colors select-none";
  const GRID_STYLE = { display: "grid", gridTemplateColumns: "repeat(7, 1fr)" } as const;

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <label className="mb-1 block text-label-caps text-secondary">{fromLabel}</label>
      <div className="flex gap-sm">
        <button
          type="button"
          className="relative flex h-[42px] w-full items-center rounded border border-outline-variant bg-surface-container-lowest pl-9 pr-3 text-left text-body-md focus:border-primary focus:ring-0"
          onClick={() => setOpen((v) => !v)}
        >
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-secondary">
            calendar_month
          </span>
          <span className={cn(from || to ? "text-on-surface" : "text-secondary")}>
            {displayText}
          </span>
        </button>
        {from || to ? (
          <button
            type="button"
            className="flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded border border-outline-variant bg-surface-container text-secondary hover:bg-surface-container-high"
            onClick={handleClear}
            aria-label="Clear dates"
          >
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        ) : null}
      </div>

      {open ? (
        <div className="absolute left-0 top-full z-50 mt-xs w-[284px] rounded-lg border border-outline-variant bg-surface-container-lowest p-md shadow-lg">
          <div className="mb-md flex items-center justify-between">
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded text-secondary hover:bg-surface-container"
              onClick={goPrevMonth}
              aria-label="Previous month"
            >
              <span className="material-symbols-outlined text-sm">chevron_left</span>
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
              <span className="material-symbols-outlined text-sm">chevron_right</span>
            </button>
          </div>

          <div className="mb-xs" style={GRID_STYLE}>
            {WEEKDAYS.map((wd, i) => (
              <div key={i} className={cn(CELL, "text-label-caps text-secondary")}>
                {wd}
              </div>
            ))}
          </div>

          <div style={GRID_STYLE}>
            {cells.map((d, i) => (
              <div
                key={i}
                className={CELL}
                onMouseEnter={() => d && setHoverDate(d)}
                onMouseLeave={() => setHoverDate(null)}
              >
                {d ? (
                  <button
                    type="button"
                    className={cn(DAY_BTN, getDayClasses(d))}
                    disabled={isDisabled(d)}
                    onClick={() => handleDayClick(d)}
                  >
                    {d.getDate()}
                  </button>
                ) : null}
              </div>
            ))}
          </div>

          <div className="mt-md flex items-center justify-between border-t border-outline-variant pt-md">
            <p className="text-body-sm text-secondary">
              {maxDays > 0 ? `Max ${maxDays} days` : ""}
            </p>
            <button
              type="button"
              className="rounded px-sm py-1 text-label-caps text-primary hover:bg-surface-container"
              onClick={handleClear}
            >
              Clear
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
