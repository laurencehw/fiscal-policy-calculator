import type { Metadata } from "next";
import { StateExplorer } from "@/components/StateExplorer";
import { statesData } from "@/lib/data";

export const metadata: Metadata = {
  title: "States",
  description: "Federal and state income tax together for the ten largest states, and what lifting the SALT cap would mean in each.",
  alternates: { canonical: "/states" },
};

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
        These are approximations from state tax parameters (Tax Foundation 2025) and Census ACS 2023 incomes. Local income, property and
        sales taxes are not modelled. The SALT figures give each state the national IRS distribution of SALT deductions (tax year
        2023), scaled to the state&apos;s average deduction; itemizer shares and averages by state are rough.
      </p>
    </>
  );
}
