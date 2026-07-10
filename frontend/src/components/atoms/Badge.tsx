import type { ReactNode } from "react";

import { cn } from "./Icon";

interface BadgeProps {
  children: ReactNode;
  className?: string;
}

export default function Badge({ children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "bg-surface-container px-2 py-0.5 rounded text-label-caps text-on-surface-variant",
        className,
      )}
    >
      {children}
    </span>
  );
}
