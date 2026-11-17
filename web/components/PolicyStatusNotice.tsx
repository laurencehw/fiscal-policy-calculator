import type { PolicyStatusInfo } from "@/lib/types";

/** Badge plus the one sentence that the score is not on the current baseline. */
export function PolicyStatusNotice({ status }: { status: PolicyStatusInfo | null | undefined }) {
  if (!status || status.on_current_baseline) return null;
  const sentence = status.baseline_sentence ?? status.note;
  return (
    <p className="statusnotice" role="note">
      <span className="tag statusbadge" data-status={status.status}>
        {status.badge}
      </span>{" "}
      {sentence}
    </p>
  );
}

/** Compact badge for lists. The sentence lives in the title. */
export function PolicyStatusBadge({ status }: { status: PolicyStatusInfo | null | undefined }) {
  if (!status || status.on_current_baseline) return null;
  return (
    <span className="tag statusbadge" data-status={status.status} title={status.baseline_sentence ?? status.note}>
      {status.badge}
    </span>
  );
}
