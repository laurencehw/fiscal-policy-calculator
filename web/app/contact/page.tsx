import type { Metadata } from "next";
import Link from "next/link";
import { contactParagraphs } from "@/lib/legal";
import { CONTACT_EMAIL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Contact",
  description: "How to write to the person who maintains the Fiscal Policy Calculator.",
  alternates: { canonical: "/contact" },
};

export default function Contact() {
  return (
    <>
      <header>
        <span className="eyebrow">Contact</span>
        <h1>Contact</h1>
        <p className="lede">
          <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
        </p>
      </header>
      <section className="reading">
        {contactParagraphs().map((text) => (
          <p key={text}>{text}</p>
        ))}
        <p>
          The project is described on <Link href="/about">About</Link>. Questions sent through{" "}
          <Link href="/ask">Ask</Link> are covered on <Link href="/privacy">Privacy</Link>.
        </p>
      </section>
    </>
  );
}
