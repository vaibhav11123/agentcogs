import { IconContext } from "@phosphor-icons/react";
import type { ReactNode } from "react";

const BASELINE_ICON_DEFAULTS = {
  size: 16,
  weight: "regular" as const,
};

export function IconProvider({ children }: { children: ReactNode }) {
  return <IconContext.Provider value={BASELINE_ICON_DEFAULTS}>{children}</IconContext.Provider>;
}
