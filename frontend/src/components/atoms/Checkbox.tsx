import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {}

export default function Checkbox({ className, ...rest }: CheckboxProps) {
  return (
    <input
      type="checkbox"
      className={cn(
        "rounded border-outline text-primary focus:ring-primary w-4 h-4",
        className
      )}
      {...rest}
    />
  );
}
