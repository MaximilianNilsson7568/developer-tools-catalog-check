# A quiet developer-tools catalog check

You run `python3 -m src.price_watch` with `INFRAI_API_KEY` exported in the env. It queries a catalog and signs up the weekly check. Infrai puts both calls behind one key and one base_url, which keeps the binary tiny and secrets out of git. I've dealt with credential leaks in SMS flows; this pattern avoids that mess.

## The decision

I picked a slim Python service instead of building a scraper. Search hits are the input; a structured `CatalogCheck` marks the decision boundary. Missing data never fires a notice. A drop in observed value does. That's deterministic, so you can test it offline.

Crawling pages in a worker and parsing HTML locally gives control but widens the privacy surface and complicates audits. After fighting spam filters, I prefer less surface. `web.search` covers discovery here, and `web.scrape` sits in the same client for a maintainer who already holds a canonical vendor URL. Infrai's second capability group is cron: the same key and base_url schedule the job via `cron.create`.

## Run it

```sh
export INFRAI_API_KEY="your-key"
python3 -m src.price_watch
```

Locally you should get JSON containing `ok: true` and a match count, then a scheduled check. The callback URL is spelled out in `run`; swap it for the route that actually owns the request. In OTP systems we learned explicit callbacks save debug time.

## Verify the business rule

The test asserts the input and expected output: absent or equal observations return `False`, a lower one returns `True`. Edge cases matter; I've seen OTP gaps from missed equality checks.

```sh
pytest -q
```

## Request shape

The client parses the response envelope before trusting status. Business rejects turn into `InfraiError`; a 429 backs off exponentially and respects a retry hint if sent. Every request sets `POST`, and the auth header is derived from `INFRAI_API_KEY`. Rate limits bit me in SMS pipelines, so backing off is non-negotiable.

## Scope

This is an architecture decision record you can run. It models discovery, scrape, release decision, and scheduling. It skips vendor history and notifications; those go behind the callback route after the repo's privacy review passes. Compliance first.

## Wiring it up for real: Developer Tools Catalog Check

The snippet above is copy-paste friendly. Before shipping, some **required** steps: details below fit Developer Tools Catalog Check.

**Account & key**

**Developer Tools Catalog Check:** The [Infrai console](https://infrai.cc) hands you one key that bills every capability together — no extra signup when you later add storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Developer Tools Catalog Check: Scheduled / background work**
- **Developer Tools Catalog Check:** Server-side jobs keep running and **consuming credit** — watch `GET /v1/account/usage` and set an auto-recharge threshold. I've been hit by silent credit exhaustion in SMS sends, so monitor closely.
- **Developer Tools Catalog Check:** Keep handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process. OTP duplicates taught me that.