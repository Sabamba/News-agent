---
name: hubspot-closed-won-analysis
description: >-
  Analyze CLOSED WON deals from HubSpot — for a rep or the whole team. Reports won
  revenue and subscriptions sold (finalized/pending/potential), breaks wins down
  by rep and by source, computes win rate and average sales-cycle length
  (created→won), and shows the monthly won trend. Use when asked to "analyze
  wins", "closed won analysis", "what's driving revenue", "win rate", "sales cycle
  length", or a rep's won-deal breakdown.
---

# HubSpot Closed Won Analysis

Explain the wins: revenue and seats booked, who's closing, which sources convert,
how fast deals close, and the trend over time.

Uses the HubSpot MCP tools (base names `get_user_details`, `search_owners`,
`search_properties`, `get_properties`, `search_crm_objects`, `query_crm_data`).
Prefix varies per session; discover with ToolSearch if needed. If HubSpot isn't
connected, say so and stop.

## Steps

1. **Connect & resolve scope.** `get_user_details`; resolve rep(s) via
   `search_owners` (or team-wide, keeping a `rep` column).
2. **Pull won deals.** `search_crm_objects` on DEAL, filter
   `hubspot_owner_id = <id>` AND `dealstage = closedwon`. Properties:
   `dealname, amount, deal_currency_code, createdate, closedate, of_licenses,
   subs__in_pending_transaction, total_potential___subs_,
   definite_deal_source_col_1__category, aeye_deal_source, hs_object_id`.
   Paginate fully. For **win rate**, also pull the `closedlost` count for the
   same scope.
3. **Revenue & seats.** Sum `amount` (won revenue; include `deal_currency_code`,
   USD here). Subscriptions: sum `of_licenses` (finalized/sold),
   `subs__in_pending_transaction` (pending), `total_potential___subs_`
   (potential). Note: some won deals carry $0 amount and record value only in
   seats — report both and flag sparse amounts.
4. **Break downs.** Wins and revenue/seats by **rep** and by **source**
   (`definite_deal_source_col_1__category`; which channels actually convert to
   revenue). 
5. **Win rate & sales cycle.** Win rate = won / (won + lost) for the scope.
   Sales cycle = `closedate − createdate` in days per won deal; report median and
   distribution. Optionally reconstruct stage dwell times from
   `hs_v2_date_entered_*` to see where winners spend time.
6. **Trend.** Group won deals by close month (`closedate`) — count and revenue —
   to show momentum.
7. **Deliver.** Lead with headline numbers (won revenue, deals won, seats sold,
   win rate, median cycle). Then breakdowns by rep and source, and the monthly
   trend. Offer a CSV.

## Guardrails

- **Always filter by the resolved owner(s).**
- **`query_crm_data` may lack `reporting-base-read`** — fall back to
  `search_crm_objects` totals / local aggregation. For monthly trend without SQL
  `DATE_TRUNC`, bucket `closedate` locally from the pulled records.
- **Data caveats:** `amount` can be blank/$0 on real wins (lean on seats);
  `aeye_deal_source` is messy free-text — clean before grouping;
  `of_licenses` vs `subs__in_pending_transaction` differ per deal, so state which
  "subscriptions sold" figure you're using.
- **Read-only.** Never modify CRM records.
