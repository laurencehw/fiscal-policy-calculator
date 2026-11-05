"use client";
// The home page's one control: swap the second proposal in the live compare.
// A plain GET form, so it works without JavaScript; with it, changing the
// select submits straight away.
import type { HomeCandidate } from "@/lib/home";

export function HomeSwap({ first, second, options }: { first: string; second: string; options: HomeCandidate[] }) {
  return (
    <form className="homeswap" method="get" action="/#example">
      <label>
        <span>Compare with</span>
        <select name="vs" defaultValue={second} onChange={(event) => event.currentTarget.form?.requestSubmit()}>
          {options
            .filter((option) => option.id !== first)
            .map((option) => (
              <option key={option.id} value={option.id}>
                {option.name} ({option.basis})
              </option>
            ))}
        </select>
      </label>
      <button type="submit">Show</button>
    </form>
  );
}
