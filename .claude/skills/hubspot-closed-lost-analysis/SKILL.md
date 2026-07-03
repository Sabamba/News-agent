---
name: hubspot-closed-lost-analysis
description: >-
  Analyze CLOSED LOST deals from HubSpot — for a rep or the whole team. Quantifies
  what was lost ($ and subscription potential), breaks losses down by rep and by
  source, reconstructs WHERE in the funnel deals died (furthest stage reached
  before loss), and measures time-to-loss. Use when asked to "analyze losses",
  "closed lost analysis", "why are we losing deals", "where do deals die", or a
  rep's lost-deal breakdown.
---

# HubSpot Closed Lost Analysis

Explain the losses: how many, how much (dollars and subscription seats), who,
which sources underperform, and — most useful — *where in the funnel deals die*.

Uses the HubSpot MCP tools (base names `get_user_details`, `search_owners`,
`search_properties`, `get_properties`, `search_crm_objects`, `query_crm_data`).
Prefix varies per session; discover with ToolSearch if needed. If HubSpot isn't
connected, say so and stop.

## Steps

1. **Connect & resolve scope.** `get_user_details`; resolve rep(s) via
   `search_owners` (or run team-wide, keeping a `rep` column).
2. **Pull lost deals.** `search_crm_objects` on DEAL, filter
   `hubspot_owner_id = <id>` AND `dealstage = closedlost`. Properties:
   `dealname, amount, createdate, closedate, of_licenses,
   subs__in_pending_transaction, total_potential___subs_,
   definite_deal_source_col_1__category, aeye_deal_source, hs_object_id` plus the
   stage-entry dates `hs_v2_date_entered_{appointmentscheduled, qualifiedtobuy,
   presentationscheduled, decisionmakerboughtin, contractsent}`. Paginate fully.
3. **Quantify the loss.** Count of lost deals; sum `amount` (note amounts are
   often blank here — report subscription potential too, from
   `total_potential___subs_`). Break down by **rep** and by **source**
   (`definite_deal_source_col_1__category`).
4. **Find where deals die (the key analysis).** For each lost deal, the furthest
   funnel stage it reached = the highest-index stage with a non-empty
   `hs_v2_date_entered_*` before it went to lost. Tabulate lost deals by
   furthest-reached stage — early-stage losses (never got past Appointment) are a
   qualification/volume problem; late-stage losses (reached Contract sent) are a
   closing/pricing problem. This distinction is the point of the analysis.
5. **Time-to-loss.** `closedate − createdate` in days; report median and the
   long tail (deals that lingered for months/years before being written off).
6. **Deliver.** Lead with totals ($ and seats lost, # deals). Then: losses by
   rep, losses by source, and the where-they-die table. Call out the biggest
   single lost opportunities by subscription potential, and any source with a
   disproportionate loss rate. Offer a CSV.

## Guardrails

- **Win rate needs the denominator.** If asked for loss *rate*, also pull
  `closedwon` counts for the same scope: loss rate = lost / (won + lost).
- **Always filter by the resolved owner(s).**
- **`query_crm_data` may lack `reporting-base-read`** — fall back to
  `search_crm_objects` totals or local aggregation of the pulled records.
- **Data caveats:** `amount` is frequently blank (lean on seats);
  `aeye_deal_source` is messy free-text (e.g. "Referal" vs "Referral") — clean
  before grouping. Losses are current-stage snapshots; furthest-reached is
  reconstructed from entered-dates.
- **Read-only.** Never modify CRM records.
