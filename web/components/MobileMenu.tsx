"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { NAV_GROUPS, NAV_ITEMS } from "@/lib/nav";
import { NavLink } from "./NavLink";

/** The phone menu: a disclosure that closes itself after a link is followed. */
export function MobileMenu() {
  const pathname = usePathname() ?? "";
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.open = false;
  }, [pathname]);
  const current = NAV_ITEMS.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  return (
    <details className="mobilemenu" ref={ref}>
      <summary>
        <span className="current">{current?.label ?? "Sections"}</span>
        <span className="menulabel">Menu</span>
      </summary>
      <div className="menugroups">
        {NAV_GROUPS.map((group) => (
          <div key={group.name} className="menugroup">
            <span className="eyebrow">{group.name}</span>
            {group.items.map((item) => (
              <NavLink key={item.href} href={item.href}>
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </div>
    </details>
  );
}
