import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const BASE =
  "inline-flex items-center justify-center gap-sm rounded font-bold uppercase tracking-wide text-label-caps transition-colors active:scale-95 disabled:opacity-50 disabled:active:scale-100";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-primary px-lg py-sm text-on-primary hover:opacity-90",
  secondary:
    "border border-outline-variant bg-surface-container px-md py-2 text-secondary hover:bg-surface-container-high",
  ghost: "p-1.5 text-secondary hover:text-primary",
  danger: "bg-error px-lg py-sm text-white hover:opacity-90",
};

export default function Button({ variant = "primary", className, ...rest }: ButtonProps) {
  return <button className={cn(BASE, VARIANTS[variant], className)} {...rest} />;
}
