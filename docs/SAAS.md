# Running ShashGuru as a service (freemium)

ShashGuru runs in two modes, selected by `DEPLOYMENT_MODE`:

| | `selfhosted` (default) | `saas` |
|---|---|---|
| Accounts / login | none | pluggable identity provider |
| LLM | `AI_BASE_URL` (your own OVMS / vLLM), as before | platform models billed in **credits**, or the user's **own API key** (BYOK) |
| Database | none | Postgres (SQLite for development) |
| Payments | none | pluggable payment provider (Stripe adapter included) |
| Abuse protection | off | rate limits, depth cap for anonymous visitors |

Everything below is about `saas`. Self-hosting is unchanged.

## The freemium model

| Who | Engine analysis | AI explanation |
|---|---|---|
| Anonymous visitor | yes, rate limited, depth capped (`ANON_MAX_DEPTH`) | no (sign in) |
| Signed-in, no credits | yes, higher limits | only with their **own key** |
| Credits (subscription and/or top-ups) | yes | platform models, charged per token |

* **Credits.** The only unit the application knows about. `1 credit = 0.001 USD` of customer price
  (`USD_PER_CREDIT`); customer price = provider price x `CREDIT_MARKUP`. Offers live in
  `backend/app/data/offers.yaml` and models/prices in `backend/app/data/models.yaml` (both overridable with
  `OFFERS_FILE` / `MODELS_FILE`). **The shipped prices are placeholders: verify them before launch.**
* **Subscription credits** are granted on every paid period and expire at its end; **purchased credits** never expire.
  Subscription credits are spent first.
* **BYOK.** Users add a key for OpenAI, Anthropic, OpenRouter or any OpenAI-compatible HTTPS endpoint. Keys are
  verified when added, encrypted at rest (AES-256-GCM, bound to the owning user) and never returned by the API.
  BYOK calls are free for the user but are recorded in the usage history.
* **How a managed call is billed.** The worst-case cost is held up front (402 if the balance cannot cover it), the stream
  runs, and the *real* cost (from the provider's usage report) replaces the hold. This also happens when the client
  disconnects mid-stream. Holds orphaned by a crash are released at start-up.

## Architecture and decoupling

```
 browser --HTTPS--> Caddy ---> static frontend (nginx)
                       \--/backend/*--> FastAPI --> Postgres  (users, ledger, keys, usage)
                                           |------> Redis     (engine cache, rate limits, analysis context)
                                           |------> engine pool (ShashChess / Alexander)
                                           |------> LLM providers
```

**Identity and payment vendors are adapters, not dependencies.** The application depends on two ports:

* `app/ports/auth.py` - `AuthProvider`: `verify_token()` -> `Identity`, `parse_webhook()` -> normalised events.
* `app/ports/payments.py` - `PaymentProvider`: `create_checkout()`, `create_portal()`, `parse_webhook()` -> normalised
  events (`TopupPaid`, `SubscriptionRenewed`, `SubscriptionChanged`, `Refunded`, `CustomerLinked`), `cancel_subscription()`.

Rules, enforced by `backend/tests/test_architecture.py` (CI fails if they are broken):

1. Only `app/adapters/**` may import a vendor SDK (`stripe`, `jwt`, ...). Nothing else may import an adapter except
   the composition root `app/bootstrap.py`.
2. The database schema has no vendor-named column. Provider ids are opaque references (`users.auth_provider` +
   `auth_subject`, `external_refs`, `subscriptions.provider`, `webhook_events.provider`).
3. Prices and offers are data. An offer maps to a provider price id under `external:` in `offers.yaml`.
4. The frontend talks to an `AuthClient` interface (`frontend/src/auth/`) and uses a plain redirect for checkout: no
   payment SDK in the browser.

### Changing identity provider

* **Auth0, Supabase, Keycloak, Cognito, Firebase... (anything that issues JWTs with a JWKS):** no code. Set
  `AUTH_PROVIDER=oidc`, `AUTH_ISSUER`, `AUTH_AUDIENCE`. Add a frontend implementation of `AuthClient`
  (`frontend/src/auth/`) and select it with `VITE_AUTH_PROVIDER`.
* **Something exotic:** add `app/adapters/auth/<name>.py` implementing `AuthProvider`, and a branch in
  `adapters/auth/__init__.py`.
* **Existing users.** Accounts are keyed by `(auth_provider, auth_subject)`. A new provider has new subjects, so users
  would get new accounts. To migrate, run a one-off script that rewrites `users.auth_provider` / `auth_subject` from an
  export of your old provider (match on e-mail). Credits, keys and history follow the user row.

### Changing payment provider

1. Add `app/adapters/payments/<name>.py` implementing `PaymentProvider` and map its webhooks to the normalised events.
2. Add a branch in `adapters/payments/__init__.py` and a value for `PAYMENT_PROVIDER`.
3. Create the same products at the new provider and add their ids under `external: <name>:` in `offers.yaml`.
4. Point the new provider's webhook at `/backend/api/v1/webhooks/payments`.

Balances, ledger and subscription state live in your database, so no credit migration is needed. Existing
subscriptions stay with the old provider until they end; keep the old adapter enabled (or migrate subscribers at the
provider) during the transition.

## Configuration

See `.env.example` for the full list. The essentials:

| Variable | Purpose |
|---|---|
| `DEPLOYMENT_MODE=saas` | turns the SaaS features on |
| `DATABASE_URL` | `postgresql+asyncpg://...` (default is a local SQLite file) |
| `KEY_ENCRYPTION_KEYS` | **required**; `v1:<key>[,v0:<old>]`; first entry encrypts |
| `AUTH_PROVIDER`, `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_ADMIN_SUBJECTS` | identity |
| `PAYMENT_PROVIDER`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | payments |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | platform keys; a model is offered only if its key is set |
| `PUBLIC_URL`, `CORS_ORIGINS`, `TRUST_PROXY` | public origin; trust `X-Real-IP` behind the proxy |
| `RATE_*`, `ANON_MAX_DEPTH` | abuse protection |

The server refuses to start in `saas` mode without an identity provider (and refuses `AUTH_PROVIDER=dev` unless
`ALLOW_DEV_AUTH=true`) or without `KEY_ENCRYPTION_KEYS`.

## Setting up the providers

**Clerk** (default identity provider)
1. Create an application; copy the *Frontend API URL* into `AUTH_ISSUER` and the publishable key into
   `VITE_CLERK_PUBLISHABLE_KEY` (a build-time value).
2. Find your own user id in the dashboard and put it in `AUTH_ADMIN_SUBJECTS`.
3. Optional but recommended: a webhook to `https://<domain>/backend/api/v1/webhooks/auth` for `user.created`,
   `user.updated`, `user.deleted`; its signing secret goes in `AUTH_WEBHOOK_SECRET`. Set `AUTH_SECRET_KEY` so that
   "delete my account" also erases the user at Clerk.

**Stripe**
1. Create a recurring product (the subscription) and one-off products (top-ups). Put their `price_...` ids in
   `offers.yaml` and keep the `credits` there in line with what you charge.
2. Add a webhook endpoint `https://<domain>/backend/api/v1/webhooks/payments` for `checkout.session.completed`,
   `checkout.session.async_payment_succeeded`, `invoice.paid`, `customer.subscription.created|updated|deleted`,
   `charge.refunded`; its signing secret goes in `STRIPE_WEBHOOK_SECRET`.
3. Enable the Customer Portal (cancellations, cards, invoices) and, for EU VAT, Stripe Tax (`STRIPE_AUTOMATIC_TAX=true`).
4. Test everything in test mode first: `stripe listen --forward-to localhost:5000/api/v1/webhooks/payments`.

**LLM keys.** Create dedicated keys with a spending limit at each provider. They are the platform's money.

## Local development of the SaaS stack

```
cd backend
DEPLOYMENT_MODE=saas AUTH_PROVIDER=dev ALLOW_DEV_AUTH=true DB_AUTO_CREATE=true \
KEY_ENCRYPTION_KEYS="$(python -c 'from app.services.crypto import generate_key; print("v1:"+generate_key())')" \
ANTHROPIC_API_KEY=... uvicorn app.main:app --port 5000

cd frontend
VITE_AUTH_PROVIDER=dev npm run dev     # sign in with any e-mail; the dev token is "dev:<subject>:<email>"
```

## Production

```
cp .env.example .env     # fill it in
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

Migrations (`alembic upgrade head`) run when the backend container starts. Caddy obtains the TLS certificate
automatically (DNS for `SITE_ADDRESS` must already point at the machine; ports 80 and 443 open).

### Go-live checklist

- [ ] **Legal review** of `/legal/terms` and `/legal/privacy` (the shipped texts are drafts), the refund policy, and
      your obligations as a seller (VAT, invoices, the 14-day withdrawal right and the digital-content waiver).
      Sub-processors to list: the identity provider, the payment provider, each LLM provider, your host.
- [ ] Prices in `offers.yaml` / `models.yaml` verified; margin checked against the current provider prices.
- [ ] Spending limits set on every platform LLM key.
- [ ] `KEY_ENCRYPTION_KEYS` stored in a password manager **outside** the server. Losing it loses every stored BYOK key.
- [ ] Stripe in live mode, webhook delivering (look for 2xx in the dashboard), Customer Portal configured.
- [ ] `./backups` copied off the machine; a restore tested at least once.
- [ ] Egress filtering (below).
- [ ] An admin (`AUTH_ADMIN_SUBJECTS`) can reach `/backend/api/v1/admin/*`; nobody else can. Caddy hides
      `/backend/metrics` and `/backend/health` from the internet; scrape them from inside the Docker network.

### Egress filtering (custom BYOK endpoints)

Users may point a key at their own HTTPS endpoint. The server rejects non-https URLs and hosts that resolve to
private, loopback, link-local or reserved addresses, when the key is saved and again on every request. DNS can change
between the check and the connection, so also block the backend container's access to private ranges at the network
level, e.g. on the Docker host:

```
iptables -I DOCKER-USER -s <backend container subnet> -d 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,169.254.0.0/16 \
         -m conntrack --ctstate NEW -j REJECT
```

(allow the subnets of `postgres` and `redis` before this rule, or run them on a separate network).

### Capacity

The engine pool lives inside the backend process, so run **one uvicorn worker** and size `ENGINE_POOL_SIZE` to the
machine (roughly one engine per physical core, leaving some for the API). Engine results are cached in Redis, and
anonymous traffic is rate limited and depth capped. If you outgrow one machine, split the engines into their own
service first (the API only needs `EngineService.analyse`).

## Operations

* `GET /api/v1/admin/engines`, `/admin/cache` - engines and cache (admin only).
* `/metrics` (Prometheus) - request counters; scrape internally.
* **Rotating the encryption key:** prepend `v2:<new>` to `KEY_ENCRYPTION_KEYS`. New keys use it; old ones stay readable.
* **Refunding a customer:** refund in the payment provider; the webhook removes the matching top-up credits
  (credits already spent stay spent). Anything else: the ledger (`credit_ledger`) is append-only, correct it with an
  `adjust` row.
* **User asks for their data / deletion:** both are self-service in *Account* (`GET /me/export`, `DELETE /me`).
  Deletion erases keys and personal data, cancels the subscription and, if configured, removes the user at the identity
  provider. The anonymised credit ledger and usage records are kept for accounting.

## Known limitations

* Single backend process (see *Capacity*).
* Rate limits are fixed windows per minute, not token buckets; bursts around a window edge can reach 2x.
* Token counts for pre-authorisation are estimated (3 characters per token, deliberately pessimistic); billing always
  uses the provider's reported usage when available.
* No in-app invoices: use the payment provider's invoices and portal.
