import type { SelectHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {}

export default function Select({ className, children, ...rest }: SelectProps) {
  return (
    <select
      className={cn(
        "w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none",
        className
      )}
      {...rest}
    >
      {children}
    </select>
  );
}
