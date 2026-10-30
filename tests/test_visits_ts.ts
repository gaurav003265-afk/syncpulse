/**
 * Test visit manager in TypeScript.
 */

import { VisitManagerTS } from "../web/src/engine/visits.ts";

function main() {
  console.log("Testing TypeScript VisitManagerTS...");
  const vm = new VisitManagerTS();

  const allVisits = vm.getVisitList("2026-10-20", null, 25, false);
  console.log(`Retrieved ${allVisits.length} visits across all villages.`);

  if (allVisits.length === 0) {
    throw new Error("No visits returned!");
  }

  // Check prioritization order
  let prevTierRank = -1;
  for (const v of allVisits) {
    let tierRank = 4;
    if (v.priority_tier === "TIER_1_CRITICAL_HIGH_RISK") tierRank = 1;
    else if (v.priority_tier === "TIER_2_OVERDUE_ROUTINE") tierRank = 2;
    else if (v.priority_tier === "TIER_3_DUE_TODAY") tierRank = 3;

    if (tierRank < prevTierRank) {
      throw new Error(`Priority tier inversion! Found tier ${tierRank} after ${prevTierRank}`);
    }
    prevTierRank = tierRank;
  }
  console.log("Tier ordering verified: Tier 1 > Tier 2 > Tier 3 > Tier 4.");

  // Test village filtering
  const ramnagarVisits = vm.getVisitList("2026-10-20", "Ramnagar", 25, false);
  console.log(`Retrieved ${ramnagarVisits.length} visits for village Ramnagar.`);
  if (ramnagarVisits.length === 0) {
    throw new Error("Expected visits for Ramnagar, got 0!");
  }
  for (const v of ramnagarVisits) {
    if (v.village !== "Ramnagar") {
      throw new Error(`Village filter failed! Expected Ramnagar, got ${v.village}`);
    }
  }
  console.log("Village filter verified.");

  console.log("ALL TYPESCRIPT VISIT TESTS PASSED!\n");
}

main();
