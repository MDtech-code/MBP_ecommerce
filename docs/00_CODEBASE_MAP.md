# MBP_ECOMMERCE — Codebase Map (Orientation Doc)

> Written as a re-onboarding artifact after a ~2.5 month break (Aug 16 → Nov 1).
> Source of truth: branch `develop` @ `69cc18f` ("remove export name of unessary file", 2026-10-27).
> Everything below was read out of the working tree, not from memory. Anything that
> could NOT be verified is called out explicitly in §7 (Reality check).

---

## 1. One-paragraph summary

A production-shaped Pakistani motorbike-parts e-commerce store: **Django 6 + DRF** backend
(17 domain apps, ~38k Python LOC) and a **React 19 + Vite 8** frontend
(~19.6k JS/JSX LOC) organized with **Feature-Sliced Design**. The backend is a REST API
(plus a single GraphQL endpoint) with JWT auth, Redis caching, Celery workers, three
Pakistani payment gateways, three courier integrations with inbound webhooks, and a
custom error-envelope/error-code contract. The frontend talks to it through one axios
instance with a token-refresh queue, TanStack Query for server state, and Zustand for
client state. Both halves run over **local HTTPS with mkcert certificates** so that the
browser treats `https://localhost:5173` and `https://localhost:8000` as first-party,
secure, cookie-sharing origins.

---

## 2. Repository topology

```
MBP_ecommerce/
├── .github/workflows/ci.yml      4 CI jobs (2 backend, 1 frontend matrix)
├── docker-compose.yml            backend, frontend, redis, celery, db
├── certs/                        localhost.pem, localhost-key.pem   (gitignored dir, 2 files committed)
├── backend/
│   ├── config/                   settings, urls, celery, logging, schema, asgi/wsgi
│   ├── apps/                     17 domain apps (see §3.2)
│   ├── templates/emails/         base + 3 partials + 7 messages (verify, reset, welcome, goodbye, otp, email-change x2)
│   ├── seed/                     data.py, seed_products.py, seed_cart.py, seed_all.py
│   ├── requirements.txt          pinned deps (⚠ UTF-16 encoded — see §7)
│   ├── pytest.ini                DJANGO_SETTINGS_MODULE=config.test_settings (⚠ missing file)
│   ├── Dockerfile
│   └── .env.example
└── frontend/
    ├── src/app|pages|widgets|features|entities|shared   FSD layers
    ├── config/aliases.js         one alias per FSD layer
    ├── scripts/verify-fsd.js     custom architecture linter
    ├── vite.config.js            HTTPS + /api & /media proxy
    ├── vitest.config.js          jsdom + scoped 90% coverage gate
    ├── Dockerfile
    └── .env.example
```

Root `README.md` exists but is **0 bytes**.

---

## 3. Backend

### 3.1 The 6-layer contract

| Layer | Location | Rule |
|---|---|---|
| Models | `models.py` (+ `managers.py`) | schema + invariants only, no business flows |
| Selectors | `selectors/*.py` | **read** queries; function-per-query, returns QuerySet/model |
| Services | `services/*.py` | **write** transactions; no DRF imports, no serializers, no HTTP |
| Serializers | `serializers.py` | validation + representation only |
| Views | `views.py` | thin: permission → serializer → service/selector → response |
| URLs | `urls.py` | `app_name` + namespaced includes |

Dependency direction is enforced by convention and documented in file headers:
`models → selectors → services → views`. The cleanest expression of this is
`apps/orders/services/order_service.py`, whose docstring states the transaction
boundary (`transaction.atomic()` steps A→L), the lock ordering
(`select_for_update()` sorted by product ID to avoid deadlocks), the `F()`-expression
rule for counter updates, and the rule that email/gateway I/O happens **after** commit.

Cross-cutting pieces in `apps/core/`:

- **`exceptions.py`** — `BaseAppError` and subclasses with an `internal` field that is never serialized.
- **`api/exceptions.py`** — `custom_exception_handler` maps any exception to one envelope:
  `{success, message, data, errors:{code, fields, non_fields}, meta:{request_id}}`.
  Also owns the single log line and the `_monitors` registry (Sentry hook).
- **`error_codes.py`** — `ErrorCode` constant registry; string values are a *public API* the frontend switches on.
- **`cache.py`** — `TwoLevelCache`: L1 locmem (60 s, 500 entries) over L2 Redis (300 s).
- **`middleware.py`** — `RequestIDMiddleware` (uuid per request, echoed as `X-Request-ID`).
- **`permissions.py`** — `IsAdmin`, `IsAdminOrReadOnly`, `IsCustomer`, `IsVerified`, `IsNotAuthenticated`, `RoleBasedProfilePermission`.
- **`throttles.py`** — `CustomAnonRateThrottle`, `CustomUserRateThrottle` + `RateLimitInfoMixin`.
- **`logging.py`** — `ExtraFieldsFormatter`; `config/logging.py` fans out one file per app into `logs/`.
- **`api/views.py` / `mixins.py`** — `BaseAPIView` used by most app views.

### 3.2 App inventory (LOC, models, responsibility)

| App | LOC | Models | Responsibility |
|---|---|---|---|
| `accounts` | 9,022 | `User`, `UserProfile`, `UserAddress`, `EmailVerificationToken`, `PasswordResetToken`, `PendingEmailChange`, `UserLoginActivity`, `SocialAccount`, `SecurityVerificationOTP`, `SecurityVerifiedSession` | custom user, auth, OTP, email change, social login, addresses |
| `products` | 5,016 | `Category`, `Brand`, `BikeModel`, `Product`, `ProductImage`, `ProductSpecification`, `StockReservation`, `LowStockAlert` | catalog, fitment by bike model, inventory |
| `logistics` | 4,800 | `Shipment`, `ShipmentStatusLog`, `CourierSettlement` | PostEx/TCS/Leopards clients + webhooks + settlements |
| `payments` | 3,120 | `PaymentTransaction`, `RefundTransaction`, `WebhookLog` | JazzCash/Easypaisa/SafePay, COD, refunds |
| `orders` | 2,752 | `Order`, `OrderShippingAddress`, `OrderItem`, `OrderStatusLog` | checkout, cancellation |
| `reviews` | 2,663 | `Review`, `ReviewVote`, `ReviewModerationLog` | verified-purchase reviews, moderation |
| `cart` | 2,235 | `Cart`, `CartItem` | guest/user cart, coupon attach |
| `returns` | 1,904 | `ReturnRequest`, `ReturnItemPhoto` | RMA flow |
| `core` | 1,714 | — | exceptions, envelope, cache, throttles, middleware, permissions |
| `notifications` | 1,110 | `Notification`, `NotificationDeliveryAttempt`, `WhatsAppCODVerification` | in-app + email order notifications |
| `contact` | 930 | `ContactMessage`, `ContactReply` | public contact form |
| `coupons` | 911 | `Coupon`, `CouponUsage` | discounts, usage limits |
| `wishlist` | 744 | `WishlistItem` | wishlist |
| `recomendations` | 334 | `UserInteractionLog`, `PersonalizedRecommendation`, `SearchLog` | interaction logging (note spelling) |
| `tax` | 292 | `TaxRate` | tax lookup |
| `common` | 270 | `TimeStampedModel` | shared base model, city/postal choices, validators |
| `analytics` | 243 | `DailySalesSnapshot`, `CourierPerformanceMetric` | snapshots |

**Mounted in `config/urls.py`:** `accounts`, `products`, `cart`, `orders`, `logistics`,
`reviews`, `returns`, `payments`, `wishlist`, `contact` (+ `/api/csrf/`, `/api/schema/`,
`/api/docs/`, `/api/redoc/`, `/graphql/`, `/admin/`).
**Not mounted (internal-only):** `coupons`, `tax`, `notifications`, `recomendations`,
`analytics`, `core`, `common`. ~57 named routes total; `accounts` alone has 26 views.

### 3.3 Extension points already built (good interview material)

Three near-identical registry patterns — all "add a class + one dict line, zero changes elsewhere":

- `accounts/auth_strategies/registry.py` — `AuthStrategyRegistry` singleton (google, facebook).
- `payments/gateways/registry.py` — `GATEWAY_REGISTRY` + `ONLINE_GATEWAYS`; COD deliberately excluded (handled by logistics).
- `logistics/couriers/registry.py` and `logistics/webhooks/registry.py` — outbound clients + inbound handlers; `self_delivery` intentionally absent.

### 3.4 Configuration stack (`backend/config/`)

- `settings.py` (456 lines) loads `backend/.env` via **django-environ**. Env-driven:
  core (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, CORS/CSRF + secure-cookie flags),
  Postgres, Redis, email/SMTP, JWT lifetime, Google/Facebook OAuth, courier secrets +
  API keys, payment credentials, Sentry DSN.
- **PostgreSQL** via `psycopg2-binary`; a commented-out `test_db` alias is still in `DATABASES`.
- **DRF**: JSON-only renderer, `IsAuthenticated` by default (so every public view must
  opt out), JWT auth, throttle rates `anon/user = 1000/hour`, custom exception handler,
  `NUM_PROXIES=1`, drf-spectacular schema class.
- **SimpleJWT**: access 59 min, refresh 1 day, `ROTATE_REFRESH_TOKENS` +
  `BLACKLIST_AFTER_ROTATION` (token_blacklist app installed).
- **Redis / Celery**: both default to `redis://127.0.0.1:6380/0`; Celery timezone
  `Asia/Karachi`, 30-min hard limit, retry-on-startup.
- **Middleware order** is deliberately commented 1→8: CORS → RequestID → Security →
  WhiteNoise → Common → Session → Auth → CSRF → Messages → XFrame; Debug Toolbar appended only when `DEBUG`.
- **Static/media**: WhiteNoise + `CompressedManifestStaticFilesStorage`; media served by
  Django only when `DEBUG` (see `config/urls.py`), otherwise the Vite `/media` proxy or a real web server must handle it.
- **Sentry**: enabled only if `SENTRY_DSN` is set; Django/Celery/Redis integrations.
- `logging.py`: builds `logs/` at import, one handler per app (17) + `django`/`celery`/root.
- `celery.py`: standard `app.config_from_object('django.conf:settings', namespace='CELERY')` + `autodiscover_tasks()`.
- `schema.py`: minimal graphene schema (`Query.me` only) — GraphQL is scaffolding, not a real surface yet.

**Background jobs that exist (no beat schedule is configured):**

- `accounts/tasks.py` — verification email, password reset, welcome, goodbye, security OTP, email-change verification (all `bind=True, max_retries=3`).
- `notifications/tasks.py` — order confirmation / cancellation / shipped / out-for-delivery.
- `payments/tasks.py` — `process_payment_webhook`.
- `logistics/tasks.py` — `logistics.process_courier_webhook`.

**Signals:** `accounts` (`user_login_failed` → login-activity/failure tracking),
`products` (Category/Brand/BikeModel save+delete → cache/tree maintenance), `cart` (empty file).

### 3.5 Why `runserver_plus` with those cert paths

```bash
python manage.py runserver_plus \
  --cert-file D:\MBP_ecommerce\certs\localhost.pem \
  --key-file  D:\MBP_ecommerce\certs\localhost-key.pem \
  0.0.0.0:8000
```

Four separate reasons, in order of importance:

1. **`runserver_plus` (django-extensions + Werkzeug)** — supports TLS flags and gives the
   Werkzeug interactive debugger. Plain `runserver` cannot serve HTTPS without wrapping it in another proxy.
2. **HTTPS is required, not cosmetic.** The frontend is served from `https://localhost:5173`
   and the API from `https://localhost:8000`. Different ports = different origins, so:
   refresh-token and CSRF cookies need `Secure` + `SameSite` semantics, `CSRF_TRUSTED_ORIGINS`
   must match exactly (`https://localhost:8000`, `https://backend:8000`, …), CORS runs with
   `CORS_ALLOW_CREDENTIALS=True`, and the `csrftoken` cookie must be readable by JS on the
   5173 origin. Browsers also refuse `Secure` cookies and certain APIs over plain HTTP.
3. **mkcert chain of trust.** `certs/localhost.pem` + `localhost-key.pem` are a
   locally-trusted leaf cert (SAN: `localhost`, `127.0.0.1`); validation only works because
   the mkcert **root CA** is installed in the OS/browser trust store. In Docker that CA has
   to be copied into the image (`update-ca-certificates`) so Node's `fetch`/Vite proxy and
   Python `requests` also trust it.
4. **`0.0.0.0:8000`** — bind all interfaces so the Compose network / another container /
   a phone on the LAN can reach it; `127.0.0.1` would be loopback-only.

Note: the `D:\...` paths are machine-specific. Inside Compose the same command becomes
`/app/certs/...` (already the case in `backend/Dockerfile` and `docker-compose.yml`).

---

## 4. Frontend (React 19 · Vite 8 · FSD)

### 4.1 Layer map

| Layer | LOC | Contents |
|---|---|---|
| `app` | 565 | `main.jsx` (providers), `App.jsx` (bootstrap gate), `providers/router.jsx`, `providers/useBootstrapAuth.js`, guards, 3 layouts, `styles/index.css` |
| `pages` | 4,949 | 11 route groups: `home`, `products`, `auth/*`, `cart`, `Checkout`, `order`, `Reviews`, `wishlist`, `profile`, `addresses`, `security` |
| `features` | 4,838 | 8 slices: `auth`, `cart`, `wishlist`, `order`, `reviews`, `profile`, `address`, `filtering` — each with `api/ (queries+mutations)`, `model/ (form hooks)`, `ui/`, `index.js` |
| `widgets` | 2,451 | `header` (topbar + navbar + 2 mega menus + mobile menu), `footer`, `home` (hero + slider), `cart` (list/summary/also-like), `product` (grid/related), `profile`, `security`, `sidebar`, `auth` |
| `entities` | 3,030 | `user` (`authStore`, `authSlice`, `ProfileView`, `AddressCard`), `product`, `category`, `cart`, `checkout` (`checkoutStore`, guards, address/payment hooks) |
| `shared` | 3,754 | `api/`, `ui/` (13 primitives + `useCountdown`), `lib/` (validators, cookies, media, theme, queryClient), `assets/`, `config/` |

`app` → `pages` → `widgets` → `features` → `entities` → `shared`. Imports are **alias-only**
(`@features/auth`), one public `index.js` barrel per slice.

### 4.2 The FSD law is executable

`frontend/scripts/verify-fsd.js` (`npm run lint:fsd`) walks every `.js/.jsx` file and flags:

1. **Hierarchy** — a layer may not import the same or a higher layer (except `app`→`app`).
2. **Cross-feature** — `features/auth` may not import `features/cart`.
3. **Deep import** — `@features/auth/model/useLoginForm` is illegal; only the slice barrel (`@shared/*` exempt).
4. **Relative cross-layer leak** — `../../../features/x` must become `@features/x`.

Note the layering of its own rules: `shared/api/interceptors.js` imports
`@entities/user` — that passes only because `checkFile` skips any file whose first path
segment is not a layer, and `shared` is exempted from Rule 1. Worth re-reading before you
quote it in an interview.

### 4.3 State & requests

- **Server state:** TanStack Query. `shared/lib/queryClient.js` sets `staleTime 5 min`,
  `gcTime 10 min`, `refetchOnWindowFocus: false`, smart retry (no retry on 4xx, 3× on
  network error, 2× on 5xx).
- **HTTP:** one axios instance, `baseURL: ""` → every call is **relative** (`/api/...`) and
  the Vite dev server proxies it. `shared/config/api.js` exposes `DIRECT_API_ORIGIN =
  ${protocol}//${hostname}:8000`, used **only** where the browser must bypass the proxy
  (token refresh, bootstrap) — the file's comment is explicit that `VITE_API_ORIGIN`
  (e.g. `https://backend:8000`) is server-side-only and would be unreachable from the browser.
- **Auth:** access token in memory/local storage via `shared/lib/authToken.js`;
  refresh token in an httpOnly cookie. `shared/api/interceptors.js` attaches `Bearer`,
  and on `401` (excluding `invalid_credentials` and the refresh URL itself) runs a
  **single-flight refresh**: `isRefreshing` flag + `failedQueue`, replay queued requests,
  hard `logout()` on refresh failure, `sessionStorage.logged_out` short-circuit.
  `429` logs `Retry-After`; `>=500` logs the payload.
- **Client state:** Zustand 5 with `devtools` + `immer` + `subscribeWithSelector`.
  `entities/user/model/authStore.js` composes `authSlice`; other stores:
  `entities/checkout/model/checkoutStore.js`, `shared/lib/themeStore.js`.
- **Service layer:** `shared/api/services/*.js` (`account`, `cart`, `order`, `product`,
  `review`, `wishlist`) + `transformers.js` (`normalizeError`, `extractData`,
  `extractPagination`, `extractErrors`) which decodes the backend error envelope and
  mirrors `shared/api/error-codes.js`.
- **GraphQL:** Apollo Client 4 is wired in `main.jsx`, but only `graphqlClient.js` +
  the backend `Query.me` exist — it runs alongside REST, it hasn't replaced anything.
- **Bootstrap:** `App.jsx` calls `ensureCsrfToken()` + `initTheme()`, then `useBootstrapAuth()`
  (silent refresh → hydrate user) and renders a full-screen "Loading…" while
  `isBootstrapping`, so guards never flash-redirect on a page reload.

### 4.4 Routing & guards

`createBrowserRouter` with three trees: **GuestRoute + AuthLayout** (`/login`,
`/register`, `/verify-email`, `/forgot-password`, `/reset-password`), **RootLayout**
(public: `/`, `/product`, `/product/:slug`), and **ProtectedRoute** inside RootLayout
for `/cart`, checkout steps, and a nested **DashboardLayout** branch
(`/profile`, `/addresses`, `/orders`, `/reviews`, `/wishlist`, `/security/*`).
Checkout uses two additional business guards — `CheckoutGuard` and `PaymentStepGuard`
from `@entities/checkout` — that enforce the address→payment step order.

### 4.5 HTTPS in dev (mirrors the backend)

`vite.config.js`:

- `isDocker = fs.existsSync("/app/certs")` → certsDir = `/app/certs` else `../certs`.
- `https` is enabled **only if** `localhost-key.pem` exists, otherwise plain HTTP (graceful degradation).
- `server.host: "0.0.0.0"`, `port 5173`, `hmr.clientPort 5173`, `watch.usePolling: true` (Windows/Docker file-watching).
- Proxy: `/api` → `VITE_API_ORIGIN` and `/media` → same target, both `changeOrigin: true, secure: true`
  — `secure: true` only works because the mkcert root CA is trusted inside the container.
- `npm run dev` = `cross-env NODE_EXTRA_CA_CERTS=../certs/rootCA.pem vite`.

Build/test: `vite.config.js` no longer carries test config — `vitest.config.js` does
(jsdom at `https://shop.example.test/`, `setupFiles: ./src/app/config/test/setup.js`,
coverage v8 with **per-file 90%** thresholds scoped to 6 foundation files).

---

## 5. Infrastructure

### 5.1 `docker-compose.yml` (Compose "develop/watch" mode, not `version:`)

| Service | Image/Build | Port | Notes |
|---|---|---|---|
| `backend` | `backend/Dockerfile` (python:3.12-slim) | 8000 | `runserver_plus` w/ `/app/certs`, mounts `./backend` + `./certs`, `env_file: backend/.env.docker`, waits on db+redis healthy, watch-syncs source and **rebuilds on requirements.txt change** |
| `frontend` | `frontend/Dockerfile` (node:24) | 5173 | `npm run dev -- --mode docker --host 0.0.0.0`, `NODE_EXTRA_CA_CERTS=/app/certs/rootCA.pem`, named volume for `node_modules` |
| `celery` | `backend/Dockerfile` | — | `celery -A config worker --loglevel=info`, same env/mounts |
| `redis` | `redis:7-alpine` | 6379 | `redis-cli ping` healthcheck |
| `db` | `postgres:16` | 5432 | named volume `postgres_data`, `pg_isready -U postgres` |
| **missing** | — | — | no `celery beat`, no nginx/gunicorn service, no backup service |

`backend/Dockerfile` installs `gcc libpq-dev libssl-dev pkg-config netcat-openbsd ca-certificates`,
copies `certs/rootCA.pem` into the trust store, then `pip install -r requirements.txt`.

### 5.2 `.github/workflows/ci.yml`

Triggers: push/PR to `develop`/`master` + `workflow_dispatch`. `permissions: contents: read`.

| Job | What it does |
|---|---|
| `test` | postgres:16 service; Python 3.12 + pip cache; `pip install -r requirements-test.txt`; `pytest --tb=short -v` (**no skips, no continue-on-error** — comment says failures in the registration rollout should stay visible); then `makemigrations --check --dry-run` |
| `redis-integration` | redis:7-alpine service; runs `apps/core/tests/test_cache_redis.py -m redis_integration` against DB 15 with `config.test_redis_settings` |
| `frontend-test` | matrix `ubuntu-latest` + `windows-latest`, Node `22.22.3`; `npm ci` → `npm run test:coverage` → `npm run build` → upload `frontend/coverage/` artifact |

Not automated: ruff/flake8, ESLint or the FSD linter, Docker build, deploy.
Lint scripts exist locally (`npm run lint`, `npm run lint:fsd`) but CI never calls them.

### 5.3 Certificates

`certs/` is in `.gitignore`, yet `localhost.pem` + `localhost-key.pem` are tracked
(force-added at some point). What the pipeline *expects*:

```
certs/
├── localhost.pem        ✔ present
├── localhost-key.pem    ✔ present
├── rootCA.pem           ✘ MISSING  ← referenced by both Dockerfiles + npm run dev
└── root.pem             ✘ MISSING  ← you mentioned it; not in the tree
```

Regeneration is `mkcert -install && mkcert -key-file certs/localhost-key.pem -cert-file certs/localhost.pem localhost 127.0.0.1`
and then exporting the root CA to `certs/rootCA.pem`.

---

## 6. Reading order (fastest path back in)

1. `backend/apps/core/exceptions.py` + `api/exceptions.py` — the response contract everything else assumes.
2. `backend/apps/orders/services/order_service.py` — the transactional core; read the module docstring twice.
3. `backend/apps/orders/{selectors,views,serializers,urls}.py` — one complete vertical slice.
4. `backend/apps/accounts/services/__init__.py` → `registration.py`, `auth.py`, `otp_service.py`, `security_otp.py` — the most intricate flow in the project.
5. `backend/config/settings.py` → `config/urls.py` — the wiring.
6. `frontend/src/app/{main.jsx,App.jsx,providers/router.jsx}` — bootstrap, guards, tree.
7. `frontend/src/shared/api/{client,interceptors,transformers}.js` — the request contract.
8. `frontend/src/entities/user/model/authSlice.js` + `features/auth/model/useLoginForm.js` — how a form talks to the store and the API.
9. `frontend/src/features/cart/**` + `pages/cart/ui/CartPage.jsx` — best example of a full FSD slice.
10. `frontend/scripts/verify-fsd.js` — your architecture rules, stated executably.

---

## 7. Reality check — repo vs. memory

Verified differences between what you described and what is actually on `develop`:

| # | Item | Finding |
|---|---|---|
| 1 | Root `README.md` | **Empty (0 bytes).** Nothing to read; this doc is now the only orientation material. |
| 2 | `backup/` folder for Postgres | **Not in the repo at all** — no folder, no script, and zero mentions of `pg_dump`/`pg_restore` anywhere. Only traces: `.gitignore` has `/backups/`, `*.dump`, `*.sql`, `*.bak`. So the dumps were always local/gitignored; the *automation* is not versioned. |
| 3 | `certs/root.pem` | **Missing.** Only `localhost.pem` + `localhost-key.pem` exist. |
| 4 | `certs/rootCA.pem` | **Missing**, but both Dockerfiles `COPY` it and `npm run dev` sets `NODE_EXTRA_CA_CERTS` to it → `docker compose build` and `npm run dev` will fail until it's exported. |
| 5 | CI status | Was **red for weeks** (latest run `40540897790`, 2026-10-27, ~1 min), failing at `Install dependencies` and `Run frontend tests`. **Green now — 3 jobs, §10/§11.** |
| 6 | `backend/requirements-test.txt` | Was **missing** (CI installed exactly this file). **Restored — §11.** |
| 7 | `backend/config/test_settings.py`, `config/test_redis_settings.py` | Were **missing** while `pytest.ini` pointed at them. **Both created — §11.** |
| 8 | `backend/apps/core/tests/` | Was **missing**. **Now holds the foundation canaries + the real-Redis lane — §11.** |
| 9 | `requirements.txt` encoding | Was **UTF-16LE with BOM** (PowerShell `>` redirect), which broke `pip install -r` on Linux/Docker/CI. **Converted to UTF-8 + LF, with a comment explaining the trap — §10.** |
| 10 | Backend tests that exist | Only `apps/{recomendations,returns,reviews,tax,wishlist}/tests.py` and an empty `apps/cart/tests/`. `pytest.ini` has `python_files = test_*.py`, which **does not match `tests.py`** → 0 tests collected, pytest exits 5. |
| 11 | Frontend test setup | `setupFiles` pointed at a **missing** `src/app/config/test/setup.js` → vitest couldn't boot. **Restored `setup.js` + `server.js`; all 35 tests in the 3 surviving files now pass — §10.** The per-file 90% coverage gate over 6 files is still unreachable (3 files are covered), so `test:coverage` stays out of CI. |
| 19 | `ErrorCode.SOCIAL_AUTH_FAILED` | Its value is `"social login fail"` — spaces, so it breaks the registry's own documented "values are snake_case" rule. All 80 values are unique; this is the only violation. Not fixed here because the file says changing a value is a breaking change for the frontend. It is allowlisted in `KNOWN_NON_SNAKE_CASE_CODES` so the rule is still enforced for the other 79. |
| 12 | Duplicate services modules | `accounts/services.py` (0 bytes) **and** `accounts/services/` package; `products/services.py` (fully commented out) **and** `products/services/` package. Python resolves the *package* first, so nothing breaks today — but these are dead, confusing duplicates. Delete both files. |
| 13 | Redis port | Settings default to **6380**, Compose publishes **6379**. `REDIS_URL` in `.env` masks this, but any unset env silently points at a dead port. |
| 14 | Celery beat | No beat service in Compose, no `CELERY_BEAT_SCHEDULE`. Tasks are all triggered from request/webhook paths, so nothing is scheduled. |
| 15 | Docker paths | `frontend/Dockerfile` has `COPY ../certs/rootCA.pem` — a `..` path escapes the build context (context is repo root) and is invalid. `dockerfile: /backend/Dockerfile` in Compose is written as an absolute path. Both need fixing. |
| 16 | `db` healthcheck | `pg_isready -U postgres` but credentials come from `backend/.env.docker` (not in repo) — if `POSTGRES_USER` isn't `postgres`, the healthcheck never passes and `depends_on: service_healthy` blocks the stack. |
| 17 | Untracked env files | `backend/.env`, `backend/.env.docker`, `frontend/.env.docker` are all gitignored and absent here — treat `.env.example` as the contract and rebuild them. |
| 18 | Minor | `apps/recomendations` (misspelled dir, referenced consistently as `apps.recomendations`, so it works but is unrenameable without a migration), `pages/Checkout` + `pages/Reviews` capitalized while siblings are lowercase, `common/choices` has no `__init__.py`, `accounts/api/__init__.py` is empty, `common/models.py` holds `TimeStampedModel` while `core/models.py` is empty. |

---

## 8. Interview talking points this codebase supports

- **Service/selector split** — quotes directly from `order_service.py`'s docstring: transaction scope, lock ordering, `F()` updates, post-commit side effects.
- **One error envelope + a typed error-code registry** — the frontend switches on `errors.code`, never on message strings.
- **Three registry patterns** for gateways/couriers/auth providers — open/closed at the edge, no service edits.
- **Two-level cache** (locmem over Redis) — process-local hot layer, shared cold layer.
- **Single-flight token refresh** with a queued-request replay — the classic "50 parallel 401s" problem.
- **Executable architecture rules** — `verify-fsd.js` turns a design convention into a linter.
- **Deliberate HTTPS-everywhere in dev** so cookie/CSRF behaviour matches production instead of being discovered there.
- **Honest CI**: "keep the full historical suite visible, no skips" is a maturity signal — but see §7.5 before claiming it's green.

---

## 9. Suggested 2-day plan

**Day 1 — backend truth.**
Repair the red feedback loop first (it's the cheapest morale win): UTF-8 `requirements.txt`,
add `requirements-test.txt`, add `config/test_settings.py` (+ `test_redis_settings.py`),
create `apps/core/tests/`, align `pytest.ini` `python_files = test_*.py tests.py`,
export `certs/rootCA.pem`. Then walk §6 items 1–5 with the tests running.

**Day 2 — frontend + infra truth.**
Fix `vitest` setup path and either narrow the coverage gate or add the missing tests.
Write the real `README.md` (setup, env matrix, run commands incl. the `runserver_plus`
line, Compose, seed). Fix the two Docker `COPY`/`dockerfile` path bugs. Then walk §6
items 6–10 and re-derive the FSD rules by running `npm run lint:fsd`.

**Open questions for you (I can't answer from the tree):**
1. Where did the Postgres backup automation live — a `.bat`/`.ps1` task on Windows, a Compose service, or a cron? Nothing is versioned, so we'd be rebuilding it from scratch.
2. Is `root.pem` the same file as `rootCA.pem`, or a separate export? Both Dockerfiles and `npm run dev` expect `rootCA.pem`.
3. Are the missing test configs (`test_settings.py`, `requirements-test.txt`, `apps/core/tests/`) something you deleted in the Aug–Oct window, or were they never committed? The single squashed commit means I can't tell.
4. `apps/recomendations` — keep the spelling, or plan a rename while the app is internal-only?

---

## 10. What this PR changed (CI green baseline)

The pipeline was red because it described a project that no longer exists. Rather than
delete it, it was **narrowed to checks that are true today** and every dead reference was
removed, so a red run now means something real.

| # | Change | Why |
|---|---|---|
| 1 | `backend/requirements.txt` re-encoded UTF-16LE → **UTF-8 + LF**, with a header comment | `pip install -r` cannot read UTF-16 on Linux. This broke Docker and both CI Python jobs before any code ran. |
| 2 | Dropped `requirements-test.txt` (missing), `config.test_settings`, `config.test_redis_settings`, `apps/core/tests/`, and the whole `redis-integration` job from CI | None of those files exist. Keeping the references guaranteed a red run forever. |
| 3 | Backend job rewritten as **`backend-check`**: `pip install -r requirements.txt` → `manage.py check` → `migrate` + `makemigrations --check` | Verifies the project still installs, every app's `AppConfig.ready()` still runs, models/settings import cleanly, and no model change has drifted away from its migration. `settings.py` requires `SECRET_KEY`, `POSTGRES_*`, `GOOGLE_*`, `FACEBOOK_*` with no defaults, so the job supplies obvious CI-only placeholder values. |
| 4 | Old matrix `frontend-test` (ubuntu **+ windows**) replaced with a single `frontend-check` job: `npm ci` → `npm test` → `npm run build` | The Windows leg existed for a Windows-only workspace; it doubles CI time for no signal. `package-lock.json` is the reproducibility guarantee. |
| 5 | Restored `frontend/src/app/config/test/{setup.js,server.js}` (MSW server, `onUnhandledRequest: "error"`, cookie/storage cleanup between tests) | The 3 surviving test files import `@app/config/test/server`; without it vitest aborted before running. **35/35 tests pass.** |
| 6 | `npm test` / `npm run test:coverage` gained `--passWithNoTests` | Removing every test file is a design decision, not a failure. |
| 7 | Added `concurrency` (cancel superseded runs) and a scope comment block at the top of `ci.yml` | Cheaper runs; the file now states what it does and does not cover. |

**Still intentionally out of CI**, each to be enabled in the PR that makes it pass:
`npm run lint` (5 eslint errors), `npm run lint:fsd` (21 FSD violations),
`npm run test:coverage` (per-file 90% gate), and any backend test run
(no backend suite exists *and* `pytest.ini` still points at a missing settings module).

**Known risk on the first run:** the `Reject missing migrations` step is the only one whose
result cannot be predicted from a static read — if a model was edited without a migration,
it will go red, and that is a true finding rather than a broken pipeline.

---

## 11. Test strategy as built (sentinel layer)

There are no feature tests yet, and inventing them top-down is what caused the previous
stall. What exists instead is a **sentinel layer**: a small set of assertions about
properties the whole project depends on. They stay green as features are added, and they
go red only when something is genuinely broken — so a red build keeps its meaning.

### What runs today

| Job | Contents | Cases |
|---|---|---|
| `test` | `apps/core/tests/test_foundation.py` + migration drift | **40** (DB-free) |
| `redis-integration` | `apps/core/tests/test_cache_redis.py` on real `redis:7` DB 15 | **13** |
| `frontend-test` | the 3 surviving files in `src/**/*.test.js` | **35** |

### `test_foundation.py` — the canaries

| Test | Invariant | Fails when |
|---|---|---|
| `test_every_project_app_is_loaded` (17) | every entry in `settings.PROJECT_APPS` is in the app registry | an app's `models.py`/`AppConfig.ready()` breaks, or a package is missing |
| `test_project_app_list_is_not_empty` | ≥10 apps declared | the parametrized test above would silently collect nothing |
| `test_root_urlconf_exposes_every_documented_namespace` | the 10 mounted namespaces exist | a `config/urls.py` include is broken or removed |
| `test_documented_top_level_routes_reverse` (4) | `csrf`, `schema`, `swagger-ui`, `redoc` reverse to `/api/...` | a top-level route is unwired |
| `test_error_code_values_are_unique` | no two `ErrorCode` names share a value | the frontend could no longer branch on a code |
| `test_error_code_values_are_snake_case` | registry matches its own stated rule (1 documented exception) | a new code is added malformed |
| `test_known_deviations_still_exist` | the allowlist hasn't rotted | an allowlisted code is renamed/deleted |
| `test_http_status_maps_to_a_stable_error_code` (11) | `_status_to_error_code` table incl. the unknown-status default | the HTTP→code contract drifts |
| `test_domain_error_response_uses_the_shared_envelope` | `{success,message,data,errors,meta}` + `errors.{code,fields,non_fields}` | the envelope shape `transformers.js` parses changes |
| `test_internal_context_is_never_serialized_into_a_response` | `exc.internal` never reaches the payload | the documented security invariant is broken |
| `test_domain_error_rejects_an_out_of_range_status_code` | `DomainError` only allows 4xx | a 500 starts leaking through the wrong exception class |

**DB-free by design.** No test uses `pytest.mark.django_db`, so pytest-django never
creates or connects to a database — the suite cannot be flaky for lack of a DB, and it
runs in ~1s. The first DB test will fail loudly the moment someone adds one, which forces
that to be a deliberate decision.

### `test_cache_redis.py` — the one lane that needs infrastructure

Against a real `redis:7`, because against LocMem every assertion would pass for the wrong
reason:

- L2 really is `django_redis.cache.RedisCache` (guards the lane itself)
- `set` writes `{"__v": ...}` to **both** levels
- an L2 hit returns `("l2_redis")` **and backfills L1**
- falsy values (`[]`, `{}`, `False`, `0`, `""`, `None`) are not mistaken for a miss — the documented reason the sentinel exists
- `delete` removes the key from both levels (SCAN-based `delete_pattern`)
- `get_or_set` builds from the database **once**, then serves from memory
- a failing builder re-raises **and leaves no lock behind**

The module calls `pytest.skip(allow_module_level=True)` unless the default cache is really
Redis, so a plain `pytest` run (which uses `config.test_settings`) skips it instead of
testing the fake and reporting a false pass.

### How tests should be added from here

Add them **where the invariant lives**, not per endpoint:

| Layer | Test it with | Example invariant |
|---|---|---|
| selector | queryset shape, no HTTP | `list_orders_for_user` never returns another user's order |
| service | transitions + invariants, DB allowed | stock never negative; coupon usage never exceeds its limit; cancel restores stock exactly once |
| view | one test per route for the wiring contract only | auth required, envelope shape, status code |
| model | only what the DB enforces | unique constraints |

The rule that kills duplication: **one test per invariant**, not per endpoint. When two
flows touch the same rule (checkout and cancellation both move stock), the rule is tested
once, at the service. `factory_boy` is already installed — use factories, not fixtures.
