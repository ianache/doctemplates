import { cn } from "./Icon";

export type StatusColor = "signed" | "draft" | "archived";

export interface StatusDotProps {
  status: StatusColor;
  label?: string;
}

const DOT_COLOR: Record<StatusColor, string> = {
  signed: "bg-green-700",
  draft: "bg-primary",
  archived: "bg-secondary",
};

const TEXT_COLOR: Record<StatusColor, string> = {
  signed: "text-green-700",
  draft: "text-primary",
  archived: "text-secondary",
};

const DEFAULT_LABEL: Record<StatusColor, string> = {
  signed: "Signed",
  draft: "Draft",
  archived: "Archived",
};

export default function StatusDot({ status, label }: StatusDotProps) {
  const resolvedLabel = label ?? DEFAULT_LABEL[status];
  return (
    <span className={cn("flex items-center gap-1.5 text-xs font-bold uppercase", TEXT_COLOR[status])}>
      <span className={cn("w-1.5 h-1.5 rounded-full", DOT_COLOR[status])} />
      {resolvedLabel}
    </span>
  );
}
