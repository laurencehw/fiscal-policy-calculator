import { identityLine, shortProducer, withoutTier, type EstimateIdentity } from "@/lib/identity";

/** One line naming who produced a figure. `short` is the table-cell form. `omitTier` drops a tier that does not grade this figure. */
export function EstimateTag({
  identity,
  short = false,
  omitTier = false,
}: {
  identity: EstimateIdentity;
  short?: boolean;
  omitTier?: boolean;
}) {
  const line = identityLine(omitTier ? withoutTier(identity) : identity);
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
