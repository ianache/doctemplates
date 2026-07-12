import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export interface InputTextProps extends InputHTMLAttributes<HTMLInputElement> {}

export default function InputText({ className, ...rest }: InputTextProps) {
  return (
    <input
      type="text"
      className={cn(
        "w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none",
        className
      )}
      {...rest}
    />
  );
}
