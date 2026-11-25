import type { Metadata } from "next";
import { Libre_Franklin, Newsreader } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import { SiteChrome } from "@/components/SiteChrome";
import { SITE_DESCRIPTION, siteUrl } from "@/lib/site";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl()),
  title: { default: "Fiscal Policy Calculator", template: "%s · Fiscal Policy Calculator" },
  description: SITE_DESCRIPTION,
  openGraph: { type: "website", siteName: "Fiscal Policy Calculator", description: SITE_DESCRIPTION },
  twitter: { card: "summary_large_image" },
};

// Self-hosted at build time, so text does not reflow when a remote stylesheet arrives.
const newsreader = Newsreader({
  subsets: ["latin"],
  style: ["normal", "italic"],
  axes: ["opsz"],
  variable: "--font-newsreader",
  display: "swap",
});
const franklin = Libre_Franklin({ subsets: ["latin"], variable: "--font-franklin", display: "swap" });

const THEME_INIT = `try{var t=localStorage.getItem("theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t;}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${newsreader.variable} ${franklin.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
      </head>
      <body>
        <SiteChrome>{children}</SiteChrome>
        {/* The analytics script is served only by Vercel; off Vercel (CI, local) it would 404. */}
        {process.env.VERCEL ? <Analytics /> : null}
      </body>
    </html>
  );
}
