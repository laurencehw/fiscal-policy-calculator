import type { Metadata } from "next";
import Link from "next/link";
import { evidence } from "@/lib/data";
import { AUTHOR_URL, CONTACT_EMAIL, REPO_URL, siteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "About",
  description: "What the Fiscal Policy Calculator is, who made it, and how to read its numbers.",
};

const TEXTBOOK_URL = "https://laurence-wilse-samson.gitbook.io/textbooks";

export default function About() {
  const oos = evidence().out_of_sample;
  return (
    <>
      <header>
        <span className="eyebrow">About</span>
        <h1>About this calculator</h1>
        <p className="sentence">
          The calculator estimates the effect of U.S. tax and spending proposals on the federal budget over ten
          years. For each policy it reports the cost and who bears it, and it says how much weight the number can
          carry.
        </p>
      </header>

      <section>
        <p>
          I built it while teaching public economics. Official scores from CBO, JCT and Treasury are the standard
          reference, but they arrive as finished numbers, and students rarely see how they were put together. This
          tool tries to show the working. Each figure on the site names the data and method behind it and the nearest
          published score, and says whether I tuned the model to that score or whether the model predicted it without
          seeing it. The site is a companion to the <a href={TEXTBOOK_URL}>Public Economics textbook</a>, and{" "}
          <Link href="/build">Build</Link> lets you start from your values rather than from a list of policies.
        </p>
      </section>

      <section>
        <h2>Who made it</h2>
        <p>
          <a href={AUTHOR_URL}>Laurence Wilse-Samson</a>, an economist (PhD, Columbia) who teaches at NYU&apos;s Wagner
          School. This is a personal research project. The views and modelling choices are my own and do not represent
          any employer.
        </p>
      </section>

      <section>
        <h2>How to read the numbers</h2>
        <p>
          I would treat every figure as an estimate with a stated source rather than as an official score. Where the model predicts a
          published score it was never tuned to, it is off by {oos.mean_abs_error}% on average across {oos.n} cases,
          and the gap varies a lot by kind of policy. <Link href="/methods">Methods</Link> gives the figures for each
          kind and lists every benchmark.
        </p>
      </section>

      <section>
        <h2>Contact and licence</h2>
        <p>
          Email <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. Source code on{" "}
          <a href={REPO_URL}>GitHub</a>.
        </p>
        <p>
          Code is under the MIT License and written content under CC BY 4.0. Please cite as{" "}
          <em>Wilse-Samson, L. (2026). Fiscal Policy Calculator.</em> {siteUrl()}
        </p>
      </section>
    </>
  );
}
