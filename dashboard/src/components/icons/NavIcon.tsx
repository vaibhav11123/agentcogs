import type { Icon } from "@phosphor-icons/react";

interface NavIconProps {
  icon: Icon;
  active?: boolean;
  className?: string;
}

export function NavIcon({ icon: IconComponent, active, className }: NavIconProps) {
  return (
    <IconComponent
      size={16}
      weight={active ? "fill" : "regular"}
      className={className}
      aria-hidden
    />
  );
}
