# Running the testing foundation

This is the implementation runbook for the [approved registration plan](registration-testing-plan.md). This first batch establishes shared tests and frontend registration-to-HTTP integration. It is **not** completion of all verification/resend/browser/concurrency work in that plan.

## Safety and architecture

- Work remains on `arena/01a0c287-mbp-ecommerce`. Only this branch is published for PR review; no direct commits/pushes to `develop` and no merge.
- pytest now defaults to `config.test_settings`. It imports the real application configuration without reading `.env`, disables Sentry initialization during that import, and replaces database/cache/mail/storage/broker settings with test-only configuration.
- The default cache fixture refuses application settings and unexpected cache backends. The opt-in Redis lane requires a dedicated namespaced backend and cleans only its namespace; it never calls Redis `clear()`/FLUSHDB. Connection failures in that lane fail loudly.
- Test database names must start with `test_mbp_`. Only `TEST_POSTGRES_*` variables select its connection; application `POSTGRES_*` values are not reused.
- Ordinary email tests use Django's local-memory backend. Celery defaults to an in-memory broker and is **not** globally eager. Service tests must assert mocked dispatch explicitly; future workflow tests will opt into eager execution.
- No production validators or middleware are disabled. No SQLite substitution for PostgreSQL constraints/transactions.
- Frontend tests use an independent Vitest config (no dev TLS/proxy setup), fresh React Query providers, RTL cleanup, restored timers/mocks, cleaned root-path cookies/storage, and MSW that rejects unexpected HTTP requests.
- Pure rule/error/countdown matrices live next to their owner. Registration page integration tests run the actual page, form hook, validators, mutation and HTTP service; only the HTTP boundary is intercepted. They do not prove the backend or browser Secure-cookie behavior.

## Frontend

Validated here with Node **22.22.3**, npm **10.9.8** and Vitest **4.1.10**. Use a supported Node version (Node 22.12+ or 24 is appropriate for the current tooling).

```bash
cd frontend
npm ci
npm test
npm run test:coverage
npm run build
```

Coverage output: `frontend/coverage/index.html` and `frontend/coverage/coverage-summary.json` (ignored by Git). A 90% per-file threshold is enforced for statements, branches, functions and lines in the explicitly listed shared foundation files in `vitest.config.js`. This is **not a repository-wide or full registration-workflow percentage**.

### Current frontend suites

| Owner | Suite | Responsibility |
|---|---|---|
| Validation | `shared/lib/validators/{rules,validate}.test.js` | Rule boundaries, rule order/short circuit, schema composition and current confirmation password |
| Response contract | `shared/api/transformers.test.js` | Null-data registration success, error flags/fields/domain/network fallbacks and 429 metadata |
| Cookies | `shared/lib/cookies.test.js` | Name matching, encoding/JSON roundtrip, clearing, malformed encoding |
| CSRF bootstrap | `shared/api/csrf.test.js` | Existing cookie, concurrent deduplication, retry after failure |
| Countdown | `shared/ui/useCountdown.test.js` | Clock boundaries, replacement, formatting, invalid date and cleanup |
| Shared input | `shared/ui/FormInput/FormInput.test.jsx` | Accessible input/error association, events, reveal button not submitting |
| HTTP adapter | `shared/api/services/accountService.test.js` | Registration/verification/resend URLs/payloads, CSRF/credentials, response/error propagation |
| Registration composition | `pages/auth/register/ui/RegisterPage.test.jsx` | Validation wiring, 201 navigation, server validation, duplicate recovery, network/500 feedback, 429 guard, in-flight duplicate-submit protection |

## Backend

Requires **Python 3.12+** for pinned Django 6. Do not downgrade Django to accommodate Python 3.11.

```bash
# Repository root
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements-test.txt
```

The existing UTF-16 `requirements.txt` and application version pins are unchanged; `requirements-test.txt` adds pytest-cov.

### Pure/shared foundation batch (does not need a running DB)

```bash
cd backend
python -m pytest \
  apps/core/tests/test_error_contract.py \
  apps/core/tests/test_throttles.py \
  apps/core/tests/test_timing.py \
  apps/accounts/tests/test_validators.py \
  apps/accounts/tests/test_cookie_utils.py \
  apps/accounts/tests/test_emails.py \
  apps/common/tests/test_email_utils.py
```

These files exercise actual domain/transport envelopes, privacy, throttling metadata, padding, custom registration rules, mail rendering and pending-email cookies. Existing exception tests have also been updated for the current formatter and safe production-error envelope; other useful suites were retained.

### PostgreSQL-backed baseline (next execution gate)

```bash
# Repository root; dedicated disposable PostgreSQL 16, loopback port 55432
# These are deliberately non-production test-only credentials.
docker compose -f compose.test.yml up -d --wait

cd backend
python -m pytest --collect-only
python -m pytest

# Repository root, after testing
docker compose -f compose.test.yml down -v
```

Defaults: user `mbp_tests`, password `test-only`, database maintenance connection `mbp_tests`, test database `test_mbp_ecommerce`. Docker service data is ephemeral (tmpfs), not an application volume. To use another dedicated server, set `TEST_POSTGRES_HOST`, `TEST_POSTGRES_PORT`, `TEST_POSTGRES_USER`, `TEST_POSTGRES_PASSWORD`, optionally `TEST_POSTGRES_DB`. Never point these at a production server. The test role needs permission to create/drop test databases.

**The entire historical backend suite is not yet claimed green.** Stale registration service/view/task tests listed in the approved plan still need repair alongside the transaction/verification implementation batch. The full-suite command above is the baseline diagnostic, not a promise of success. No failures have been hidden with skips or xfails.

## Execution record — first batch, 2026-09-20

| Check | Actual result |
|---|---|
| Initial frontend baseline | No test files found; Vitest exited 1 |
| Shared regression run before fixes | 83 cases: 76 passed, 7 failed. Six failures exposed four product defects; one test incorrectly supplied an absent Axios envelope and was corrected to the supported `{data: {}}` input. |
| Registration composition before guard fix | 101 cases: 100 passed; duplicate-submit test observed two outbound requests |
| Final `npm ci` | Passed; lockfile usable. npm audit reports 18 vulnerabilities (8 moderate, 10 high); no blanket dependency upgrades applied. |
| Final `npm run test:coverage` | **9 files, 101 passed, 0 failed/skipped**, scoped threshold gate passed |
| Scoped shared coverage | **100% statements/lines/functions; 99.31% branches** across the eight explicitly included files (remaining branch: FormInput's name fallback when no placeholder) |
| `npm run build` | Passed; existing large-bundle warning remains |
| Scoped ESLint | Passed for the added frontend tests/harness/config and modified frontend modules (see implementation notes below) |
| Python compile/static syntax check | Passed for test settings, fixtures, new/updated backend tests and validator module; this is not pytest execution |
| `git diff --check` | Passed |
| Backend pytest / migrations / transaction tests | **Not executed**: sandbox Python is 3.11.2. Python 3.12 runtime downloads failed (TLS/network); PostgreSQL apt download also failed. No compatible runtime or PostgreSQL service was available. |
| CI | Updated for isolated settings/PostgreSQL test connection, Python 3.12, Node 22.22.3, PRs to develop, npm ci and scoped coverage upload; **not executed remotely** |
| Real browser / live broker | Not executed or added in this batch |

### Small production changes paired with regressions

1. Cookie reader now treats malformed percent encoding as an absent cookie instead of throwing.
2. Countdown handles invalid timestamps as inactive `0:00` rather than `NaN:NaN`.
3. Shared error extraction exposes a normalized fallback message when no field/non-field detail is available; field-only validation remains inline without a redundant banner.
4. FormInput exposes an accessible name, invalid state and uniquely associated error description. Password reveal remains a non-submit button.
5. Registration has a synchronous in-flight guard, plus pending/rate-limit checks, so same-frame or programmatic submit events cannot bypass the disabled button. The guard resets after settlement and existing retry-after-error integration remains green.
6. Backend strong-password wrapper now attaches `PASSWORD_TOO_WEAK` to each Django ValidationError message; Django does not propagate a code supplied to a list-valued error. A regression test is added, but **runtime verification of this backend change remains outstanding**.

Existing frontend testing documentation describes older folders and unit-only mocking. This runbook and `vitest.config.js` describe the current setup; the approved plan remains the roadmap.

## Remaining work — do not mistake this batch for completion

1. Obtain the supported backend runtime, run the shared tests and full collection/baseline, and fix any actual failures. Validate the new settings/fixtures in that runtime before declaring Phase 0 complete.
2. Finish shared backend manager/token/selector/decorator tests and validate persisted factory password hashes. Complete interceptor and verification lifecycle tests on the frontend.
3. Repair stale registration service/view/task tests while implementing approved post-commit dispatch, no-op resend, verification-cookie cleanup and secret-safe logging regressions. **The request-data print and raw token logging identified in the plan have not been removed in this batch.**
4. PostgreSQL rollback and concurrency tests, real API contracts, verification/resend composition and frontend stale-error/lifecycle race behavior.
5. Playwright with isolated full stack/mail capture, Secure-cookie checks and login eligibility boundary.
6. Run the updated CI and add browser/live-service lanes after the backend baseline is runnable. The existing full backend suite remains mandatory; historical failures were not hidden or made continue-on-error. CI uses no SMTP/Sentry credentials. A separate mandatory Redis job was added in the follow-up below.

The next batch should start with backend execution and the remaining reusable backend prerequisites, not duplicate the already-tested frontend validators/error adapters.


## Redis review follow-up — 2026-09-22

### Which review suggestions apply?

1. **Add real Redis coverage: accepted, with separate test lanes.** Existing
   `core/tests/test_cache.py` tests lock-related control flow and L2→L1 backfill
   with a mocked L2. Those tests remain useful but are not Redis integration.
   `TwoLevelCache.delete()` catches/logs `delete_pattern` errors, so a LocMem
   backend does not necessarily raise to its caller; it can instead leave stale
   L2 data. Real Redis checks are necessary to catch this adapter mismatch.
2. **Port 1 is not a typo.** `_test_env.REDIS_URL` is an intentionally unusable
   base-import sentinel. Default test settings subsequently replace CACHES and
   Celery with local/in-memory backends. The Redis lane never uses that URL:
   `TEST_REDIS_URL` defaults to `redis://127.0.0.1:56379/15` locally and CI supplies
   `redis://127.0.0.1:6379/15` explicitly.
3. **No PostgreSQL port mismatch.** Final DATABASES reads `TEST_POSTGRES_PORT`.
   Local test Compose publishes `55432:5432`; CI supplies `5432` to match its
   `5432:5432` mapping. `_test_env.POSTGRES_PORT` is only an import-time default.
4. **Non-eager Celery is deliberate.** `.delay()` publishes to `memory://`, but
   without an in-process worker the task does not execute. Service tests must
   mock dispatch and assert arguments/call counts. Task tests call `.run()` or
   `.apply()`; workflow tests explicitly enable eager execution. Eager mode
   still does not prove delivery through an actual broker/worker. The Redis
   cache lane does not change Celery's broker.

### Two lanes, not one misleading substitute

- Default `config.test_settings`: real local L1; ordinary cache tests mock L2;
  no Redis requirement. Redis integration tests are explicitly skipped here.
- `config.test_redis_settings`: actual django-redis backend, DB **15**, unique
  `test_mbp_<uuid>` key prefix per process, independent L1s in contention tests.
  A disposable Redis instance is still required: a DB number alone is not a
  guarantee that no developer data exists there.
- Cleanup uses django-redis's prefix-aware `delete_pattern("*")`, **never**
  FLUSHDB/FLUSHALL. A test confirms an unrelated raw sentinel survives cleanup.
- The CI `redis-integration` job is mandatory and separate from the historical
  backend job, so an unrelated collection failure cannot prevent this lane
  from being attempted. There is no continue-on-error.

The 10 Redis cases cover serialized/falsy values, L2→L1 backfill, invalidation
and nonmatching-key survival, namespace cleanup safety, atomic lock contention,
normal in-flight stampede prevention with two independent L1s, and lock release
on builder failure. These bounded coordination checks **do not prove** lock
ownership after lease expiry, behavior after maximum wait, or all multi-process
failure scenarios; those remain separate production cache risks.

### Run the Redis lane locally

From the repository root, with Python 3.12+ dependencies installed:

```bash
docker compose -f compose.test.yml up -d --wait redis
cd backend
python -m pytest apps/core/tests/test_cache_redis.py --ds=config.test_redis_settings -m redis_integration
cd ..
docker compose -f compose.test.yml down -v
```

The local Redis port is **56379**, intentionally different from a developer's
usual 6379/6380. A dedicated service on another port can be selected with
`TEST_REDIS_URL`; settings reject URLs not using DB 15. Do not point it at
production. The ordinary test suite remains runnable without starting Redis.

### Verification status

The initial PR's GitHub frontend job passed; its full backend test step failed
(after dependencies installed successfully). Log download failed in this sandbox,
so the cause is not attributed to Redis or PostgreSQL port settings.
Runtime validation is now available from GitHub Actions run
[35700605194](https://github.com/MDtech-code/MBP_ecommerce/actions/runs/35700605194),
for code commit `41854e5`:

- **redis-integration: passed** on Python 3.12 with the Redis 7 service.
- **frontend-test: passed**, including the coverage gate and build.
- **test (full historical backend suite): failed** at the pytest step; migration
  check was consequently skipped. Detailed log download still fails from this
  sandbox, so the precise failure cause is not asserted here.

The draft PR remains blocked on the full backend suite. Redis success is not a
claim that every backend workflow or every cache concurrency scenario passes.
