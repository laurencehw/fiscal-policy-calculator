// Site nav and footer, in Balance of Power's layout.
import Link from "next/link";
import { AUTHOR_URL, REPO_URL } from "@/lib/site";
import { NAV_GROUPS } from "@/lib/nav";
import { MobileMenu } from "./MobileMenu";
import { NavLink } from "./NavLink";

const [SCORE, TOPICS, LEARN] = NAV_GROUPS;

export function SiteChrome({ children }: { children: React.ReactNode }) {
  return (
    <div className="wrap">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <nav className="site noprint" aria-label="Site">
        <div className="siterow">
          <Link href="/" className="wordmark">
            Fiscal Policy Calculator
          </Link>
          <span className="navlinks">
            {LEARN.items.map((item) => (
              <NavLink key={item.href} href={item.href}>
                {item.label}
              </NavLink>
            ))}
          </span>
        </div>
        <span className="sectionlinks">
          {[SCORE, TOPICS].map((group) => (
            <span key={group.name} className="navgroup" aria-label={group.name}>
              {group.items.map((item) => (
                <NavLink key={item.href} href={item.href}>
                  {item.label}
                </NavLink>
              ))}
            </span>
          ))}
        </span>
        <MobileMenu />
      </nav>
      <main id="main" className="main">
        {children}
      </main>
      <footer className="noprint">
        <p>
          Budget figures are ten-year estimates from the calculator&apos;s Python engine, computed nightly, unless a
          page says otherwise (Social Security and Generations look further ahead). Where an agency or research
          group has published a score for the same policy, the page shows it and how far apart the two are.
          Agreement on a calibrated policy is by construction, and the page says so.
        </p>
        <p>
          A personal, non-commercial project by{" "}
          <a href={AUTHOR_URL} rel="author">
            Laurence Wilse-Samson
          </a>
          , not affiliated with any employer. Code and methods: <a href={REPO_URL}>GitHub</a>.{" "}
          <Link href="/contact">Contact</Link>
          {" · "}
          <Link href="/privacy">Privacy</Link>.
        </p>
      </footer>
    </div>
  );
}
