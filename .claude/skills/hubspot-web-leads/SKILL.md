---
name: hubspot-web-leads
description: >-
  Connect to HubSpot and pull all web leads (contacts that originated online —
  website form fills, organic/paid search, social, referrals, etc.) into a
  single, complete, de-duplicated list. Use when the user asks to "get web
  leads", "pull leads from HubSpot", "export our inbound/website leads", or
  otherwise wants the full set of web-sourced leads from the CRM.
---

# HubSpot Web Leads

Pull the **complete** set of web leads from HubSpot and hand them back to the
user in a usable form. "Complete" is the whole point: never sample, never stop
at the first page, and always verify the returned count against the reported
`total`.

This skill uses the HubSpot MCP tools (prefixed `mcp__HubSpot__`). If those
tools are not available in the session, tell the user the HubSpot MCP server
must be connected first and stop.

## What counts as a "web lead"

A web lead is a **contact** whose original source is online rather than offline.
Portals differ in exactly how they track this, so **discover the real property
before filtering** — do not hardcode assumptions.

The default definition, unless the user says otherwise:

- Object type: `contacts`
- Original source is a web channel — i.e. `hs_analytics_source` is **not**
  `OFFLINE` (common web values: `ORGANIC_SEARCH`, `PAID_SEARCH`, `PAID_SOCIAL`,
  `SOCIAL_MEDIA`, `EMAIL_MARKETING`, `REFERRALS`, `DIRECT_TRAFFIC`,
  `OTHER_CAMPAIGNS`).
- Optionally narrowed to `lifecyclestage = lead` when the user means "leads"
  specifically rather than "all web-sourced contacts".

Some portals instead track web leads via a dedicated `hs_lead_status`, a
"Lead source" custom property, membership in a specific list, or the standalone
**Leads** object. When in doubt, confirm the definition with the user before
pulling — a wrong filter silently returns the wrong people.

## Steps

### 1. Confirm the connection and portal

Call `mcp__HubSpot__get_user_details` (and `get_organization_details` if useful)
to confirm you're pointed at the expected HubSpot account. Report the portal so
the user knows which CRM the leads come from.

### 2. Discover the right properties

Do not guess internal property names. Run:

```
mcp__HubSpot__search_properties {
  "objectType": "CONTACT",
  "keywords": ["analytics_source", "lead_status", "lead_source", "lifecyclestage"]
}
```

Then, for any enumeration property you'll filter on (e.g. `hs_analytics_source`,
`lifecyclestage`, `hs_lead_status`), call `mcp__HubSpot__get_properties` to read
the exact enum values before building the filter. Use the internal names and
values verbatim.

### 3. Pull ALL matching contacts (paginate to completion)

Use `mcp__HubSpot__search_crm_objects`. Request only the properties you need so
results stay narrow and fast. A good default property set:

```
["firstname","lastname","email","company","jobtitle","phone",
 "hs_analytics_source","hs_analytics_source_data_1","lifecyclestage",
 "hs_lead_status","createdate","hs_object_id"]
```

Filter for the web-lead definition. Example filter for "online source"
(everything except offline), optionally AND-ed with lifecycle stage = lead:

```
filterGroups: [{
  filters: [
    { propertyName: "hs_analytics_source", operator: "NEQ", value: "OFFLINE" }
    // add: { propertyName: "lifecyclestage", operator: "EQ", value: "lead" }
  ]
}]
```

Sort by `createdate DESCENDING` for stable pagination.

**Paginate until you have every record:**

1. First call returns a `total` and an `offset`. Note the `total`.
2. Keep calling with the returned `offset` (and `limit: 200`, the max) until you
   have collected `total` records or the results stop advancing.
3. If `total` is very large, tell the user the count up front before pulling
   everything, and prefer `mcp__HubSpot__query_crm_data` (SQL) for large exports
   or when you also need counts/aggregates.

De-duplicate on `hs_object_id` (or `email`) as you accumulate.

### 4. Verify completeness

Before presenting results, confirm the number of collected records matches the
`total` the API reported. If they don't match, say so explicitly rather than
presenting a partial list as complete.

### 5. Deliver

Ask (or infer from the request) the desired output:

- **Quick view** — a Markdown table of name, email, company, source, created
  date, with the total count.
- **File export** — write CSV or JSON to disk (e.g. `web_leads.csv`) and report
  the path and row count.

Always lead with the count: e.g. "Pulled 214 web leads (matches HubSpot's
reported total of 214)."

## Guardrails

- **Completeness over speed.** A partial list presented as complete is a bug.
  Always reconcile collected count vs. `total`.
- **Discover, don't assume.** Property names and enum values vary per portal;
  resolve them with `search_properties` / `get_properties` every run.
- **Don't invent a definition.** If "web lead" is ambiguous for this portal,
  confirm the filter with the user before pulling.
- **Least data needed.** Request only the properties required for the task.
- **Read-only.** This skill retrieves leads; it does not create, edit, or delete
  CRM records.
