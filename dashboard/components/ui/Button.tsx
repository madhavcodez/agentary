import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import Spinner from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-emerald-600 hover:bg-emerald-500 text-white border-transparent focus:ring-emerald-500/30",
  secondary:
    "bg-gray-800 hover:bg-gray-700 text-gray-200 border-gray-700 focus:ring-gray-500/30",
  ghost:
    "bg-transparent hover:bg-gray-800 text-gray-400 hover:text-gray-200 border-transparent focus:ring-gray-500/30",
  danger:
    "bg-red-600 hover:bg-red-500 text-white border-transparent focus:ring-red-500/30",
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "px-2.5 py-1 text-xs gap-1.5",
  md: "px-4 py-2 text-sm gap-2",
  lg: "px-5 py-2.5 text-sm gap-2",
};

const SPINNER_SIZE: Record<Size, "sm" | "md"> = {
  sm: "sm",
  md: "sm",
  lg: "md",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      icon,
      children,
      className,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          "inline-flex items-center justify-center font-medium rounded-lg border transition-colors duration-150",
          "focus:outline-none focus:ring-1",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          VARIANT_CLASSES[variant],
          SIZE_CLASSES[size],
          className,
        )}
        {...props}
      >
        {loading ? <Spinner size={SPINNER_SIZE[size]} /> : icon}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";

export default Button;
