// Site nav and footer, in Balance of Power's layout.
import Link from "next/link";
import { AUTHOR_URL, REPO_URL } from "@/lib/site";
import { NavLink } from "./NavLink";

export function SiteChrome({ children }: { children: React.ReactNode }) {
  return (
    <div className="wrap">
      <nav className="site" aria-label="Site">
        <div className="siterow">
          <Link href="/" className="wordmark">
            Fiscal Policy Calculator
          </Link>
          <span className="navlinks">
            <a href={`${REPO_URL}/blob/main/docs/METHODOLOGY.md`}>Methods</a>
          </span>
        </div>
        <span className="sectionlinks">
          <NavLink href="/explore">Explore</NavLink>
          <NavLink href="/build">Build</NavLink>
          <NavLink href="/tailor">Tailor</NavLink>
          <NavLink href="/social-security">Social Security</NavLink>
          <NavLink href="/tracker">Bill tracker</NavLink>
        </span>
      </nav>
      {children}
      <footer>
        <p>
          Every figure is a ten-year estimate from the calculator&apos;s Python engine, computed nightly. Where an
          agency or research group has published a score for the same policy, the page shows it and how far apart
          the two are. Agreement on a calibrated policy is by construction, and the page says so.
        </p>
        <p>
          A personal, non-commercial project by{" "}
          <a href={AUTHOR_URL} rel="author">
            Laurence Wilse-Samson
          </a>
          , not affiliated with any employer. Code and methods: <a href={REPO_URL}>GitHub</a>.
        </p>
      </footer>
    </div>
  );
}
