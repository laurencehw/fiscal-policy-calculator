"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/** A nav link that marks itself current on its own page and on the pages beneath it. */
export function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname() ?? "";
  const current = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link href={href} aria-current={current ? "page" : undefined}>
      {children}
    </Link>
  );
}
