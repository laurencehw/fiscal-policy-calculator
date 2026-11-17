import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { presets } from "./data";
import { plainDescription } from "./format";

const INTERNAL = /Phase E|provenance pass|\*\*|🟡/;
const STALE_SAVES = /Saves ~\$100B|Saves ~\$500B|Saves ~\$1\.1T/i;

test("preset descriptions shipped to Explore are plain language", () => {
  for (const info of presets()) {
    const shown = plainDescription(info.description);
    assert.doesNotMatch(info.description, INTERNAL, info.id);
    assert.doesNotMatch(shown, INTERNAL, info.id);
    assert.doesNotMatch(info.description, STALE_SAVES, info.id);
    assert.doesNotMatch(shown, STALE_SAVES, info.id);
  }
  const page = fs.readFileSync(new URL("../app/explore/[id]/page.tsx", import.meta.url), "utf8");
  assert.match(page, /plainDescription/);
});
