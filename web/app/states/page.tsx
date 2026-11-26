import type { Metadata } from "next";
import { StateExplorer } from "@/components/StateExplorer";
import { statesData } from "@/lib/data";
import { pageMeta } from "@/lib/meta";

export const metadata: Metadata = pageMeta({
  title: "States",
  description: "Federal and state income tax together for the ten largest states, and what lifting the SALT cap would mean in each.",
  path: "/states",
});

export default function StatesPage() {
  const data = statesData();
  return (
    <>
      <header>
        <span className="eyebrow">Ten largest states · {data.year} law</span>
        <h1>Federal and state taxes together</h1>
        <p className="sentence">
          How much income tax a household pays to Washington and to its state, at each income level, and what lifting the cap on the
          state and local tax deduction would do in each state.
        </p>
      </header>
      <StateExplorer data={data} />
      <p className="note">
        These figures are approximations built from state tax parameters (Tax Foundation, 2025) and Census ACS 2023 incomes. I do
        not model local income, property or sales taxes in the income-tax curves. The SALT figures use each state&apos;s own IRS
        distribution of state and local tax deductions (Statistics of Income, tax year 2022), by income class, at tax-year-2022
        amounts.
      </p>
    </>
  );
}
