---
name: hubspot-open-funnel
description: >-
  Analyze the OPEN sales pipeline (deals not yet closed won/lost) from HubSpot —
  for one rep, several reps, or the whole team. Produces the open-stage funnel
  with counts per stage, subscription potential, source mix, and last-contact
  recency, and flags stale/at-risk deals. Use when asked to "show the open
  funnel/pipeline", "what's in play", "open deals by stage", "which deals are
  going cold", or a rep's active pipeline.
---

# HubSpot Open Funnel

Show what is still *in play* for a rep or team: open deals (everything except
Closed won and Closed lost), organized by stage, with the signals that decide
whether they'll close — subscription potential, deal source, and how recently
each was touched.

Uses the HubSpot MCP tools (base names `get_user_details`, `search_owners`,
`search_properties`, `get_properties`, `search_crm_objects`, `query_crm_data`).
The tool prefix varies per session — discover with ToolSearch if a direct call
fails. If HubSpot isn't connected, say so and stop.

## Scope

- **Object:** DEAL, pipeline "Sales Pipeline" (verify; confirm which pipeline if
  the portal has more than one).
- **Open stages** (exclude the two closed stages): `appointmentscheduled`,
  `qualifiedtobuy`, `presentationscheduled`, `decisionmakerboughtin`,
  `contractsent`. Discover the live stage set with
  `get_properties(DEAL, ["dealstage"])` — never hardcode.

## Steps

1. **Connect & resolve scope.** `get_user_details` for the portal. Resolve the
   rep(s) with `search_owners`; "me/my" → current user's `hubspot_owner_id`. For
   a team view, run per-owner and combine, keeping a `rep` column.
2. **Pull open deals.** `search_crm_objects` on DEAL, filter
   `hubspot_owner_id = <id>` AND `dealstage IN (<the open stages>)`. Request only
   what you need: `dealname, dealstage, amount, createdate, closedate,
   notes_last_contacted, of_licenses, subs__in_pending_transaction,
   total_potential___subs_, definite_deal_source_col_1__category,
   aeye_deal_source, hs_deal_stage_probability, hs_object_id`. Paginate to the
   full `total` (limit 200).
3. **Build the open funnel.** Count deals per open stage in pipeline order
   (current-stage snapshot). Optionally add the historical furthest-reached view
   (from `hs_v2_date_entered_*`) if the user wants true progression.
4. **Layer the signals.**
   - **Subscription potential** = `total_potential___subs_` (this portal often
     leaves deal `amount` blank, so seats are the better size signal — surface
     both, note if amounts are sparse).
   - **Source** = `definite_deal_source_col_1__category` (clean channel) and
     `aeye_deal_source` (free-text detail).
   - **Recency** = `notes_last_contacted`; compute days-since-contact vs. today.
5. **Flag at-risk deals.** Stale = `notes_last_contacted` older than ~6 months
   or blank. The highest-value at-risk deals (big potential + stale/blank
   contact) are the headline — sort a "needs attention" list by subscription
   potential descending.
6. **Deliver.** Lead with totals (open deal count, total subscription potential,
   weighted pipeline = Σ amount×probability, # stale). Then a stage-ordered
   funnel table and, on request, a CSV / the needs-attention list.

## Guardrails

- **Always filter by the resolved owner(s)** — a missing owner filter returns
  the whole company.
- **`query_crm_data` (SQL/GROUP BY) needs the `reporting-base-read` scope**,
  which this connection may lack. If it errors, fall back to `search_crm_objects`
  (read `total` per filter, or pull the records and aggregate locally).
- **Discover stages/fields every run;** don't assume names or that `amount` is
  populated.
- **Read-only.** Never modify CRM records.
