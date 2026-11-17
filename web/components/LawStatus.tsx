import { chipText } from "@/lib/lawStatus";
import type { LawStatus } from "@/lib/types";

/** The chip alone, with the note as its title, for lists. */
export function LawChip({ status }: { status: LawStatus }) {
  return (
    <span className="lawchip" data-status={status.status} title={status.note}>
      {chipText(status)}
    </span>
  );
}

/** The chip and its note, for a proposal page. */
export function LawStatusNote({ status }: { status: LawStatus }) {
  return (
    <p className="lawstatus" data-status={status.status}>
      <LawChip status={status} /> {status.note} <span className="tag">Status as of {status.as_of}.</span>
    </p>
  );
}
