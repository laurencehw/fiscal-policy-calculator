import { identityLine, shortProducer, type EstimateIdentity } from "@/lib/identity";

/** One line naming who produced a figure. `short` is the table-cell form. */
export function EstimateTag({ identity, short = false }: { identity: EstimateIdentity; short?: boolean }) {
  const line = identityLine(identity);
  if (!short) {
    return (
      <span className="tag estimatetag" data-kind={identity.kind} data-producer={identity.producer}>
        {line}
      </span>
    );
  }
  return (
    <span className="tag estimatetag short" title={line} data-kind={identity.kind} data-producer={identity.producer}>
      <span className="sr-only">{line}</span>
      {shortProducer(identity)}
    </span>
  );
}
