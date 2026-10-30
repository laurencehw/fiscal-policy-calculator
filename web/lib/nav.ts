// The site's sections, grouped by what a visitor came to do. The header, the
// phone menu, the home page and the sitemap all read this one list.

export type NavItem = { href: string; label: string; blurb: string };
export type NavGroup = { name: string; items: NavItem[] };

export const NAV_GROUPS: NavGroup[] = [
  {
    name: "Score a policy",
    items: [
      { href: "/explore", label: "Explore", blurb: "Every preset proposal, with its ten-year score beside the published score it is checked against." },
      { href: "/build", label: "Build", blurb: "Put policies together, or start from your values, and see the package total." },
      { href: "/tailor", label: "Tailor", blurb: "Set your own income or corporate tax rate change and score it." },
    ],
  },
  {
    name: "Topics",
    items: [
      { href: "/social-security", label: "Social Security", blurb: "Pick reforms from SSA's actuaries and see how far they go toward 75-year solvency." },
      { href: "/states", label: "States", blurb: "Federal and state income tax together in the ten largest states." },
      { href: "/generations", label: "Generations", blurb: "Long-run effects of capital taxes and Social Security, and who carries them by age." },
      { href: "/tracker", label: "Bill tracker", blurb: "Bills in Congress with a ten-year budget estimate, updated nightly." },
    ],
  },
  {
    name: "Learn",
    items: [
      { href: "/ask", label: "Ask", blurb: "Ask a budget question; answers use these scores and cite their sources." },
      { href: "/classroom", label: "Classroom", blurb: "Public finance problem sets checked against the model." },
      { href: "/methods", label: "Methods", blurb: "How a policy is scored, and how far the scores sit from published ones." },
      { href: "/about", label: "About", blurb: "Who made this and how to read its numbers." },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((group) => group.items);
