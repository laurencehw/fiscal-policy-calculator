import type { Metadata } from "next";
import Link from "next/link";
import { privacyParagraphs } from "@/lib/legal";
import { CONTACT_EMAIL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Privacy",
  description: "What the Fiscal Policy Calculator does with a visit, and what Ask sends to Anthropic.",
  alternates: { canonical: "/privacy" },
};

export default function Privacy() {
  return (
    <>
      <header>
        <span className="eyebrow">Privacy</span>
        <h1>Privacy</h1>
        <p className="lede">
          Questions on Ask go to Anthropic and are not stored here. Write to{" "}
          <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> about this policy.
        </p>
      </header>
      <section className="reading">
        {privacyParagraphs().map((text) => (
          <p key={text}>{text}</p>
        ))}
        <p>
          <Link href="/ask">Ask</Link> is the only page that sends what you type off this site.{" "}
          <Link href="/contact">Contact</Link> is email, which you send yourself.
        </p>
      </section>
    </>
  );
}
