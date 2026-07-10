import { cn } from "../../lib/cn";

interface IconProps {
  name: string;
  className?: string;
}

export default function Icon({ name, className }: IconProps) {
  return <span className={cn("material-symbols-outlined", className)}>{name}</span>;
}
