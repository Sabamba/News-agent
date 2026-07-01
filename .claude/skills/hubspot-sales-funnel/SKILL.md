---
name: hubspot-sales-funnel
description: >-
  Show a salesperson's sales funnel from HubSpot — record counts at each
  pipeline/lifecycle stage for one rep (or "me"), in stage order, with
  stage-to-stage and overall conversion rates. Use when the user asks to "show
  my funnel", "build a sales funnel for <rep>", "funnel/pipeline breakdown by
  stage", "conversion rates for a rep", or wants a rep's deal or lifecycle
  funnel.
---

# HubSpot Sales Funnel

Build a **funnel** for one salesperson: how many records sit at (or have passed
through) each stage of their sales process, in the correct stage order, with the
conversion rate between stages and the overall top-to-bottom conversion.

This skill uses the HubSpot MCP tools (base names `search_owners`,
`search_properties`, `get_properties`, `search_crm_objects`, `query_crm_data`,
`get_user_details`). The tool prefix varies by session (e.g. `mcp__HubSpot__…`
or a per-connection id) — discover the actual names with ToolSearch if a direct
call fails. If the HubSpot MCP server isn't connected, say so and stop.

## What "funnel" means here

A funnel is an **ordered** set of stages, each with a count, where every stage
is a subset of the one above it. Two common shapes — pick based on the request,
and confirm with the user if ambiguous:

1. **Deal-pipeline funnel** (default for "sales funnel for a rep"): DEAL records
   grouped by `dealstage`, ordered by the pipeline's stage order, typically
   ending in **Closed Won**. **Closed Lost** is tracked separately as leakage,
   not as a bottom stage.
2. **Lifecycle funnel**: CONTACT records grouped by `lifecyclestage`
   (Subscriber → Lead → MQL → SQL → Opportunity → Customer).

## Steps

### 1. Confirm the connection

Call `get_user_details` to confirm the portal and to capture the current user's
owner id (needed for "my funnel").

### 2. Resolve the salesperson (owner)

- "my" / "me" / "I" → use the current user's `hubspot_owner_id` from
  `get_user_details`.
- A named rep → resolve with `search_owners` (by name/email) to get their
  `hubspot_owner_id`. If multiple match, ask which one.
- Every count in this skill is filtered by `hubspot_owner_id = <resolved id>`.
  Without that filter you'd report the whole company's funnel, not the rep's.

### 3. Discover the stages (never hardcode)

- Deal funnel: `get_properties(objectType: "DEAL", propertyNames: ["dealstage"])`
  returns the stage options **in pipeline order** with labels. If the portal has
  multiple pipelines, confirm which pipeline the user means and filter on
  `pipeline` too — stage sets differ per pipeline. Note which stages are
  Closed Won vs Closed Lost.
- Lifecycle funnel:
  `get_properties(objectType: "CONTACT", propertyNames: ["lifecyclestage"])`
  for the ordered stage values.

### 4. Count records per stage for that rep

Preferred (one call, exact): `query_crm_data` with a GROUP BY —

```
SELECT dealstage, COUNT(*), SUM(amount_in_home_currency)
FROM DEAL
WHERE hubspot_owner_id = '<OWNER_ID>'
GROUP BY dealstage
```

(For a lifecycle funnel: `SELECT lifecyclestage, COUNT(*) FROM CONTACT WHERE
hubspot_owner_id = '<OWNER_ID>' GROUP BY lifecyclestage`.)

If `query_crm_data` fails with a missing scope (e.g. `reporting-base-read`),
**fall back** to `search_crm_objects`: one call per stage with `limit: 1`,
filtering `hubspot_owner_id = <id>` AND the stage, and read the `total` count.
Sum deal `amount` by including it in a small paged pull if $ per stage is wanted.

Scope the funnel to a time window (e.g. deals created this year) only if the
user asks — otherwise report all-time for the rep.

### 5. Compute the funnel

Order stages by the pipeline/lifecycle order from step 3, then:

- **Count** at each stage.
- **% of entry** — each stage's count ÷ the top (first) stage's count.
- **Step conversion** — each stage's count ÷ the previous stage's count.
- **Overall conversion** — bottom (won) stage ÷ top stage.
- Report **Closed Lost** separately as leakage, plus total pipeline `$` and won
  `$` if amounts were pulled.

Note the funnel-counting caveat: `dealstage`/`lifecyclestage` is the record's
**current** stage, so a deal that already closed won't be counted in earlier
stages. State this — "counts are current-stage snapshots, not cumulative
historical flow" — unless you reconstruct flow from `hs_v2_date_entered_*`
properties (only do that if the user needs true historical conversion).

### 6. Deliver

Lead with the rep's name and the headline conversion, then a stage-ordered
table:

| Stage | Count | % of entry | Step conv. | $ (optional) |

Offer a **visual funnel** as a follow-up: a self-contained HTML funnel/bar chart
via the Artifact tool. Keep Closed Lost visually distinct (leakage), not stacked
as the final stage.

## Guardrails

- **Always filter by the resolved owner.** A missing owner filter silently
  returns the whole company — the #1 way this goes wrong.
- **Discover stages and their order every run;** never assume stage names or
  ordering. Confirm the pipeline when there's more than one.
- **Keep the funnel honest:** stages are current-stage snapshots unless you
  explicitly reconstruct historical flow; Closed Lost is leakage, not a stage.
- **Read-only.** This skill reports the funnel; it does not modify CRM records.
