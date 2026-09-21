# Registration testing plan — shared foundations first

**Status:** Approved by MD. Implementation is in progress; see [testing runbook and execution record](testing.md). The review below records the original baseline, not a claim that all findings are resolved.
**Review date:** 2026-09-20
**Repository baseline:** `05cb58e80403d77890c16625f4c9b8aa271d2563`
**Working branch:** `arena/01a0c287-mbp-ecommerce` (branched from `develop`; `develop` remains untouched).

## 1. Objective and scope

Build a reusable testing foundation, then prove the email/password registration journey. Do not recreate shared validation, error-handling, or infrastructure tests for every future workflow.

The repository has meaningful architectural separation: backend serializers, services, selectors, managers, transport infrastructure and email adapters; frontend FSD layers, service adapters, mutation hooks, form hooks and presentation components. This supports layered testing. It is not, by itself, proof that every module follows every SOLID principle, or that the site is a measurable percentage complete.

**Proposed registration boundary:** submit registration → create unverified account and related records → verification email → verify token → verified account and welcome email. Include resend as the recovery path. Include only a login boundary check (unverified denied / verified eligible), not a full login suite.

**Not part of this first delivery:** social registration, password reset, OTP, account changes, checkout, full cart behavior, product/catalog tests, pagination/cache utility expansion unrelated to registration, load testing, and broad architectural refactoring. Existing unrelated tests remain intact.

## 2. Review evidence and execution limits

This plan is based on source inspection of the active registration path, its dependencies, account tests, core test structure and relevant assertions, test configuration, CI and existing frontend testing documentation.

**No test suite was run and no coverage percentage has been measured.** Static mismatches below are not represented as executed test failures. This checkout has no frontend `node_modules`; the inspected Python environment has no reported Django/pytest installations and is Python 3.11.2, whereas the pinned Django 6 needs Python 3.12 or newer. Dependency setup and isolated infrastructure belong to Phase 0.

Other setup findings:

- `backend/pytest.ini` uses `config.settings`, which reads environment configuration and connects to PostgreSQL/Redis. No dedicated test settings file is present.
- `backend/requirements.txt` is UTF-16 encoded; tooling must read it correctly. Normalize only as an explicit setup change if needed, not by blindly rewriting dependency versions.
- `frontend/package.json` already lists Vitest, RTL, user-event, jsdom and MSW. No frontend test/spec files were found.
- `frontend/vite.config.js` points to `src/app/config/test/setup.js`, which is absent.
- The coverage script exists but `@vitest/coverage-v8` is not declared. Backend coverage tooling is also not pinned in the inspected requirements.
- Existing `docs/frontend/06-testing-strategy.md` describes the older `src/test/` structure. Keep its isolation strategy for unit tests, but supplement it with genuine multi-layer integration tests; mocking every layer cannot prove the workflow wiring.
- CI triggers pushes to `develop`/`master` and PRs to `master`, not PRs to `develop`. It uses Python 3.12 and Node 20, while the README describes newer versions. Reconcile supported runtimes against actual package engines and production, rather than treating README claims as authoritative.

## 3. Actual dependency map

### Frontend

```text
pages/auth/register/ui/RegisterPage.jsx
  → features/auth/register/model/useRegisterForm.js
      → shared/lib/validators/{rules,schemas,validate}.js
      → shared/api/transformers.js (normalizeError, extractErrors)
      → shared/ui/useCountdown.js
      → features/auth/api/useAuthMutations.js (useRegister)
          → shared/api/services/accountService.js
              → shared/api/client.js + registered interceptors
              → shared/lib/cookies.js (CSRF header)
  → POST /api/accounts/register/
  → navigate /verify-email

pages/auth/verify-email/ui/VerifyEmailPage.jsx
  → features/auth/model/useVerifyEmail.js
      → pending_verification_email cookie
      → verify/resend mutation hooks → accountService
  → POST /api/accounts/verify-email/ or /resend-verification/
  → navigate /login on successful verification
```

### Backend

```text
RequestIDMiddleware → DRF authentication/permission/throttle pipeline
  → RegisterView(BaseAPIView)
      IsNotAuthenticated + CustomAnonRateThrottle
      → RegisterSerializer → shared account validators
      → register_user service
          normalize email/name + mask email for logging
          transaction.atomic:
            email_exists → UserManager.create_user
            create_user_profile
            create_cart_for_user
            create_verification_token
          dispatch send_verification_email_task.delay(user.id, token)
      → created_response (201, data currently null)
      → set_email_cookie

send_verification_email_task
  → require_user decorator → send_email adapter
      → HTML template + plain-text alternative → email backend

VerifyEmailView → EmailVerificationSerializer → verify_email
  → token state checks → atomic token consumption + user verification
  → welcome-email task

ResendVerificationView → ResendVerificationSerializer → resend_verification
  → lookup user → new token + verification-email task

Shared response boundary:
  APIResponseMixin + BaseAPIView + core exception handler
  → {success, message, data, errors, meta}
```

Sources are under `backend/apps/accounts/`, `backend/apps/core/`, `backend/apps/cart/selectors/cart.py`, and the frontend paths above. The active registration implementation is `accounts/services/registration.py`; do not target the legacy sibling `accounts/services.py` merely because its name looks relevant.

## 4. Existing-test disposition

**Policy:** preserve valid behavioral assertions; extend incomplete suites; replace obsolete tests or sections only where their contract/target is wrong. An incomplete file does not justify discarding its good tests. Final keep decisions require collection, execution and branch review.

| Existing location | Static assessment | Proposed action |
|---|---|---|
| `core/tests/test_exceptions.py` | Imports `_format_errors`, absent from current implementation; current formatter is `_format_drf_errors(data, status_code)`. | Repair stale tests against current public error contract, not merely rename the import. Preserve monitor/status/envelope cases that remain valid. |
| `core/tests/test_mixins.py` | Substantial response-helper and request-ID tests exist. | Retain valid cases; audit expected domain envelopes; extend rate-limit metadata and parity between direct view errors and global handler. |
| `core/tests/test_middleware.py` | Covers UUID generation, header and response propagation. | Candidate to retain largely unchanged after execution; do not repeat full UUID matrix in registration. |
| `core/tests/test_permissions.py` | Includes anonymous/authenticated `IsNotAuthenticated` cases and HTTP checks. | Retain valid cases; add only registration permission wiring at endpoint level. |
| `core/tests/test_cache.py`, `test_pagination.py` | Existing shared suites, not direct registration-rule owners. | Leave intact; baseline execution may reveal independent issues, tracked separately. |
| `accounts/tests/test_models.py` | Useful user defaults, properties, uniqueness and basic superuser checks. | Retain; extend manager boundaries and verification-token lifecycle in dedicated modules. |
| `accounts/tests/test_serializers.py` | Useful basic validation and confirmation-removal checks; mostly field-presence assertions, repeated confirmation-removal case. | Retain representative wiring tests; put exhaustive custom rule matrices in validator tests; strengthen error codes and boundary cases. Serializer tests do not themselves return HTTP 400, despite current names. |
| `accounts/tests/test_services.py` | Useful happy path/dispatch failure checks. Patches removed `ensure_email_unique`, and `registration.Cart` / `registration.EmailVerificationToken`, which are not imported there. Expects `EMAIL_ALREADY_EXISTS`, but service raises generic `ConflictError`. | Repair outdated sections, retain valid assertions, add rollback at each step, exact task arguments, nested transaction and concurrency cases. Resolve duplicate-code contract first. |
| `accounts/tests/test_views.py` | Expects `data.email`, but view currently returns `data=null` and sets a cookie. Asserts `AnonRateThrottle` membership, whereas view declares `CustomAnonRateThrottle`. Duplicate-code mismatch also exists. | Replace stale expectations after contract approval; retain status/envelope tests. Exercise actual throttling instead of class membership alone. |
| `accounts/tests/test_tasks.py` | Patches `apps.accounts.tasks.send_mail`; current verification task uses `send_email` and `require_user`. | Rewrite obsolete task tests, preserving recipient/link/retry/missing-user intentions; email rendering gets its own adapter suite. |
| `common/tests/factories.py` | Reusable factories exist. `skip_postgeneration_save=True` plus `set_password` post-generation warrants a persisted-hash check. | Reuse and validate factories before relying on them for authentication tests. Use actual `Role` enum rather than silent fallbacks. |
| `backend/conftest.py` | Cache cleanup suppresses all errors and uses configured caches. | Isolate test caches first; do not clear any developer/production Redis. Avoid silently hiding integration-environment failures. |
| Frontend | Tool dependencies/scripts present, setup missing, no test/spec files found. | Establish setup and layered tests without duplicating frameworks. |

Additional fixture concern: fixtures in `common/tests/conftest.py` are scoped to that directory, not automatically shared with sibling `accounts/tests`. Deliberately expose cross-app fixtures through root conftest or an explicit test plugin; keep app-specific fixtures local.

## 5. Contract decisions and defects to investigate

These must not be concealed by changing tests to agree with whatever code currently does. Record intended behavior, reproduce it with a test, then obtain approval for any production change.

| ID | Source evidence / risk | Decision and recommended test |
|---|---|---|
| D1 | Registration returns 201 with null data plus a pending-email cookie; old test expects email in body. | Recommend retain current cookie-based contract; verify attributes and normalized value, no password/token leakage. Confirm whether body email is intentionally omitted. |
| D2 | Duplicate service raises `ConflictError` → `conflict_error`; old tests expect `EMAIL_ALREADY_EXISTS`. | Agree generic vs email-specific machine code. Assert top-level and non-field codes separately. |
| D3 | `resend_verification` logs a no-op for a verified user but does not return; token creation/dispatch follows. | Recommend verified user is a true no-op as documented. Test no new token/no dispatch and identical outward response for missing/verified/unverified users. |
| D4 | First successful verification returns before cookie-clearing code; already-verified branch clears cookies. Frontend removes a localStorage key, while reading the pending email from a cookie. | Agree cookie cleanup on first success and on idempotent success; test real browser behavior, not only mock storage calls. |
| D5 | Registration/verification dispatch tasks after their local atomic block, not via `transaction.on_commit`. An enclosing transaction may still roll back. | Recommend dispatch only after outermost commit. Add outer transaction rollback/commit tests; no claim of an existing outbox or delivery guarantee. |
| D6 | Verification checks expiry and used state before already-verified user state; a replayed used token is an error, not idempotent success. No row lock is used in this service. | Confirm replay policy. Recommend at-most-once state transition/welcome dispatch under concurrent verification; test with real PostgreSQL transactions. |
| D7 | `RegisterView` prints `request.data` (contains passwords); verification hook logs token to console; verification service logs raw token context. | Security priority: test that credentials and verification secrets never reach captured stdout/logs. Removal/redaction needs approved code changes. |
| D8 | `extractErrors` returns a form message only from `non_fields`; network normalization has only a top-level message. | Test visible network/malformed-server failure feedback. Do not accept a silently failing form as correct merely because normalization worked. |
| D9 | Form submit hook has no pending/rate-limit guard, although UI disables the button; server errors override client errors and are not cleared by field edits. | Test repeated submit/Enter, retry and correction after server rejection. Agree stale-error clearing and submission guarding behavior. |
| D10 | Verification hook uses module-global promise/token/status state. | Test StrictMode, remount, token change during an in-flight request, stale response navigation and retry after failure. Avoid fixing tests with resets that hide real lifecycle bugs. |
| D11 | Backend password policy includes configured Django validators; frontend rule only checks length and all-numeric passwords. | Backend remains authoritative. Test a server-only rejection reaches UI; decide any UX parity changes separately. Include password whitespace handling in serializer review. |
| D12 | Registration uses anonymous IP throttle; `register_email` rate exists in settings but is not attached here. | Test actual configured throttle, not a presumed 3/day email limit. Decide whether additional abuse protection is required; timing padding on only the domain-error path is not proof of enumeration resistance. |

CSRF also needs explicit characterization: sending an `X-CSRFToken` header does not establish backend enforcement. Registration uses JWT authentication through DRF defaults. Test the actual anonymous/session/JWT cases with CSRF-enforcing clients; confirm intended policy before asserting that missing CSRF must be rejected.

## 6. Reusable ownership matrix — test these before the workflow

Each ID represents a maintained capability suite, not a new framework. Exhaustive boundaries live with their owner; endpoint/UI tests retain a few representative wiring checks.

| ID | Owner / source | Required cases | Layer / dependency boundary |
|---|---|---|---|
| B1 | `core/exceptions.py`, `core/api/exceptions.py` | Domain/system/DRF/unexpected exceptions; permitted statuses; field/non-field shapes; code preservation; internal context never serialized; DEBUG off safe errors; monitor failure isolation; 429 headers/metadata. | Pure/transport tests, small real HTTP fixtures. No account DB needed for pure contracts. |
| B2 | `core/api/{mixins,views}.py`, `core/middleware.py` | Success/error envelope, nulls, created status, request ID header/body agreement, caller metadata preserved, rateLimit reset ISO value. | Existing core suites; do not build a parallel response harness. |
| B3 | `core/permissions.py`, `core/throttles.py`, `core/timing.py` | Anonymous/authenticated rejection; allowed/blocked limits; remaining never negative; reset boundary; no-history path; most restrictive metadata; fresh identity; deterministic padding below/at/above minimum. | Fake clock, isolated cache; dedicated Redis smoke where relevant. No real sleep. |
| B4 | `accounts/validators.py` (registration functions) | Email normalization/format; name whitespace/two-word rule; configured password failures; exact password match; codes and original return values. | Parameterized pure/settings tests; do not reproduce Django's entire implementation test suite. |
| B5 | `accounts/managers.py`, user/profile/token models | Required identity fields, normalization, persisted password hashing, unusable password behavior, safe defaults, uniqueness; token UUID/default expiry, before/at/after expiry, used/valid state, persisted mark-used. | Real test DB for persistence. Own exhaustive manager/token cases here. |
| B6 | `accounts/selectors/user_selectors.py`, cart creation selector | Normalized existence lookup, exclusion, exact linkage of profile/token/cart, relevant one-to-one/unique constraints. | DB tests; no cart pricing/checkout expansion. |
| B7 | `core/decorators.py`, `accounts/emails.py`, `common/utils/email_utils.py` | Decorator injects user and forwards arguments; missing user no-op; unrelated DB error not swallowed; masked normal email; HTML/plain-text rendering, context overrides, recipient/from/subject, send errors propagate. Define malformed masking-input contract. | Decorator DB tests + local-memory mail backend; no SMTP. |
| B8 | `accounts/utils/cookie_utils.py` | Pending-email set/clear names and matching path; Secure, SameSite=Lax, readable, 900-second lifetime. | Response tests + one real-browser roundtrip. Readability is intentional UX, not authentication. |
| F1 | `shared/lib/validators/` | Each registration rule boundary; first-error ordering, missing values, empty schema, no input mutation, dynamic password confirmation. | Vitest pure units. |
| F2 | `shared/api/transformers.js` | Success null-data unwrap; 400 field/409 domain/429 metadata; 401/403/5xx flags; null/network/non-JSON responses; fallback message; rate-limit structured vs fallback/reset/expired data. | Pure functions with fake time. Shared sample envelopes validated against backend contracts. |
| F3 | `shared/lib/cookies.js`, `shared/api/csrf.js` | Exact cookie-name matching, absent/encoded/JSON values, malformed encoding policy; set/clear; existing-CSRF short circuit, single in-flight bootstrap, retry after failure. | jsdom + MSW. Use browser tests for Secure/SameSite semantics. |
| F4 | `shared/ui/useCountdown.js` | Missing/past/future target, formatting, target replacement, zero boundary, cleanup/unmount, malformed timestamp policy. | Hook tests with fake timers; do not sleep. |
| F5 | `shared/ui/FormInput`, toast used by registration | Value/change/blur/error rendering, password reveal without submitting, accessible names/error association, keyboard operation, visible form error. | RTL component tests; accessibility shortcomings become explicit issues, not CSS snapshots. |
| F6 | `shared/api/services/accountService.js`, client/interceptors | Registration/verify/resend method, URL, payload, credentials and CSRF choices; unwrap success and preserve failures; public 400/409/429 errors are not refresh-retried. Characterize stale-token behavior on public routes. | Adapter tests; one initialized-client integration. Full refresh-token suite can follow separately. |

Reuse means future workflows depend on these tested contracts. It does **not** mean skipping their tests later: shared suites continue running in CI, and changed contracts require owner tests plus dependent integration checks.

## 7. Registration-specific test matrix

### Backend composition

| ID | Scenario | Observable assertions |
|---|---|---|
| R1 | Valid serializer payload | Normalized email/name; password validated; confirmation removed; only intended service arguments; protected extra fields cannot grant staff/admin/verified state. |
| R2 | Missing/blank/null/invalid fields and mismatched confirmation | Proper field and machine code; no persistence or task dispatch. Exhaustive rule combinations stay in B4. |
| R3 | Successful service | Exactly one linked user/profile/cart/token; unverified customer defaults; exact task user ID and string token; no accidental dependence on inactive signals. Password hash matrix stays in B5, with one wiring assertion here. |
| R4 | Duplicate and normalized duplicate | Approved 409 domain contract; no additional related rows/email. |
| R5 | Failure at user/profile/cart/token step | Transaction rollback leaves no partial new aggregate; unrelated existing data unchanged; no email dispatch. Patch collaborators where imported by `registration.py`, not removed symbols. |
| R6 | Unique-constraint race | A deterministic mocked IntegrityError test plus a separate PostgreSQL concurrent-registration test; one aggregate survives and losing request gets agreed conflict response. |
| R7 | Broker failure / enclosing transaction | Agreed persisted-account recovery behavior; no dispatch on outer rollback; dispatch only when committed if D5 approved. |
| R8 | Registration HTTP success and rejection | Real URL/view/serializer/service/DB; 201 envelope and cookie, no secrets in body; representative 400, duplicate 409, actual throttled 429 with Retry-After, authenticated rejection, unsupported method, safe unexpected 500, correlated request ID. |
| V1 | Verification state matrix | Valid UUID token, malformed UUID, unknown UUID, expired, used, already-verified with unused token; exact approved outcomes, no writes/tasks on rejection. |
| V2 | Verification atomicity/concurrency | Token/user changes roll back together on failure; concurrent consumption cannot trigger duplicate welcome side effects under approved policy; broker failure does not unverify account. |
| V3 | Resend | Missing/verified/unverified inputs; same outward success; only eligible accounts create token/dispatch; normalized email; send failure and retry recovery. Confirm whether old unused tokens remain valid or are revoked before writing assertions. |
| W1 | Backend workflow | Register through API → inspect captured verification message/link → verify through API → assert verified user/consumed token and welcome message → replay behavior; include one resend after expired/lost token case. No service mocks; local email backend/eager task execution in this lane only. |

### Frontend composition

- **Form hook units:** no blur validation before first submit; invalid submit blocked; latest form state used; client error clears/revalidates after changes; confirmation tracks changed password; server field/form errors; navigation only on success; pending/throttle behavior and correction/retry semantics.
- **Page units:** use a narrow hook stub to test pending/disabled/countdown/error states and field wiring. Do not retest every validation string here.
- **Page integration (MSW):** real RegisterPage + form hook + validators + mutation + service + HTTP client. Exercise success/navigation, one 400 field error, 409, 429 expiry/retry, network and 500 failure, keyboard submit/double-submit behavior. No mock of the unit under integration.
- **Verification hook/page:** cookie present/absent, URL token verification, successful navigation, invalid/expired token UI, resend pending/success/failure, StrictMode and token-switch race cases (D10). Isolate module state between independent tests without hiding within-test races.
- **Small real-browser suite (proposed Playwright):** (1) register → captured email link → verify → login boundary; (2) expired token → resend → recover; (3) registration cookie/CSRF and 429 countdown smoke. Use a test-only mail sink, never actual inboxes or a production-accessible token endpoint.

## 8. SOLID and no-duplication rules for the tests

1. **Single responsibility:** validators own rule matrices, adapters own delivery/transport, services own orchestration/transactions, views own HTTP policy, hooks own state transitions, pages own rendering.
2. **Open/closed:** add parameterized cases and small factory traits, not a giant configurable test framework or inherited test-class tree.
3. **Substitution:** fakes must respect actual signatures, exceptions and return envelopes. Maintain adapter/contract tests so a mock returning the wrong shape cannot make the workflow falsely green.
4. **Interface segregation:** provide small fixtures (`registration_payload`, `mail_outbox`, isolated client/clock) instead of an all-purpose fixture initializing unrelated stores and infrastructure.
5. **Dependency inversion:** substitute external boundaries (SMTP, broker publication, network, clock) through existing seams; do not introduce production abstractions solely to satisfy tests without a demonstrated need.
6. Mock at the lookup location. For example, registration rollback tests patch `apps.accounts.services.registration.create_cart_for_user`; task tests patch `apps.accounts.tasks.send_email`; adapter rendering tests exercise real templates.
7. Real ORM and PostgreSQL for constraints and transactions. Mocking `transaction.atomic` or all selectors would not prove rollback.
8. No tests that only assert a mock returns its configured value. Prefer persisted state, visible UI, outbound arguments and forbidden side effects.
9. Share setup and contract samples, not implementation algorithms copied into expected-value helpers. Keep a few representative cross-layer checks even where unit coverage overlaps.
10. A failing intended-behavior test is evidence of a defect, not permission to weaken expectations. Temporary xfails require a specific issue/reason and must remain visible; critical unresolved cases block completion.

## 9. Proposed organization

Extend existing backend files where still coherent; split only when distinct ownership makes a file easier to maintain.

```text
backend/config/test_settings.py                    # proposed isolated settings
backend/conftest.py                               # genuinely shared fixture registration
backend/apps/core/tests/
  test_exceptions.py, test_mixins.py, test_middleware.py, test_permissions.py
  test_throttles.py, test_timing.py, test_decorators.py  # new focused owners
backend/apps/common/tests/
  factories.py, test_email_utils.py
backend/apps/accounts/tests/
  test_models.py, test_managers.py, test_validators.py, test_selectors.py
  test_serializers.py, test_services.py, test_views.py, test_tasks.py
  test_emails.py, test_cookie_utils.py, test_email_verification.py
  test_registration_workflow.py
backend/apps/cart/tests/test_registration_cart.py

frontend/src/app/config/test/setup.js              # configured global setup
frontend/src/app/config/test/                      # integration render harness/MSW server
frontend/src/shared/{lib,api,ui}/.../*.test.{js,jsx} # colocated capability tests
frontend/src/features/auth/.../*.test.{js,jsx}      # hook/mutation tests
frontend/src/pages/auth/.../*.test.jsx             # page units/integration
frontend/e2e/registration.spec.js                  # proposed browser suite
```

Use FSD public exports for cross-slice integration. Colocated owner tests may import the module they test directly. Tests may use an app-level harness; production shared code must not import higher layers or test helpers. Do not reorganize production folders as part of testing setup. Inspect `tests.py`/`tests/` coexistence and discovery explicitly; current pytest pattern `test_*.py` excludes `tests.py` scaffolds.

## 10. Implementation phases and gates

### Phase 0 — Agree contracts and make execution safe

- Approve scope and D1–D12 decisions; distinguish accepted current behavior from intended corrections.
- Align Python/Node runtime with supported dependencies; install reproducibly from committed pins/lockfile. Add missing coverage/browser tooling only as approved development dependencies.
- Add isolated test settings/env defaults without real credentials. Mandatory social-provider variables receive harmless test values. Sentry and external network delivery disabled before settings initialization, not merely in a late fixture.
- PostgreSQL test database only. Separate Redis namespace/database for Redis checks; local-memory cache for ordinary tests. Never flush configured application caches.
- Local-memory email backend; broker dispatch mocked in service/API tests. Explicit eager tasks only in task/workflow lanes. No blanket autouse task mock that would hide missing workflow wiring.
- Create frontend setup; fail on unhandled MSW requests; fresh QueryClient per test, no retry surprises, clean cookies/storage/stores, restore fake timers, interceptors and module caches.
- Run collection and baseline suites. Save actual failures categorized as setup/stale contract/product defect/unrelated issue. No global suppression to achieve green.

**Gate:** safe isolated execution, test discovery understood, contracts decided, baseline recorded.

### Phase 1 — Shared backend and frontend capability tests

Implement/repair B1–B8 and F1–F6 in dependency order. Validate factory password persistence. Keep unrelated suites untouched except clearly necessary baseline fixes approved separately.

**Gate:** shared critical contracts pass; uncovered branches are documented; deliberate sample faults (wrong error code, missing timer cleanup, leaked internal data) are caught by assertions.

### Phase 2 — Account adapters and orchestration

Serializer wiring, service atomicity, task dispatch/retry, verification/resend behavior, and database concurrency. Replace the stale test sections identified in section 4. Raise minimal product fixes separately from test setup.

**Gate:** happy/failure/rollback paths pass on PostgreSQL; intended security and recovery behavior is demonstrated.

### Phase 3 — HTTP and frontend integration

Real endpoint wiring and UI-to-MSW composition; share reviewed success/error contract examples between backend assertions and frontend handlers so mocks cannot drift unnoticed.

**Gate:** field, domain, rate-limit and network failures are visible/actionable; credentials and sensitive token data do not leak; lifecycle race tests pass.

### Phase 4 — Browser workflow and CI

Use an isolated full stack and mail sink. Test with HTTPS where needed for Secure cookies. Run a small browser suite, then add CI lanes and publish reports. For any hosted preview, bind servers to `0.0.0.0`, allow the preview host, and keep browser API calls same-origin through a proxy; no browser-facing localhost backend URL.

Proposed CI lanes: backend fast tests, PostgreSQL transaction/integration tests, frontend unit/integration + build, and browser smoke. Redis/Celery live-worker smoke can be separate: eager execution does not prove broker delivery. Extend triggers to PRs targeting `develop` after approval; no direct writes to `develop`.

**Gate:** documented commands reproduce results locally and in CI; workflow and critical regression tests pass without retries masking failures.

## 11. Coverage, reporting and completion

Proposed targets for approval, not existing measurements:

- Track **branch coverage**, not only line coverage, for touched capability and registration modules.
- Aim for at least **90% branch coverage** in focused custom pure utilities and registration/verification orchestration. Review every uncovered critical branch regardless of the percentage.
- Every required case ID in this plan must map to a test or an explicit accepted deferral. Security, rollback, permission and token-consumption cases cannot be traded for a coverage score.
- Do not impose an artificial repository-wide threshold on unrelated unfinished workflows. Establish a baseline, then prevent regressions in the scoped modules.
- Keep unit suites deterministic and inexpensive; mark transactional concurrency/browser/live-service tests separately. Document any added pytest markers (`db_integration`, `workflow`, etc.) because strict markers are enabled.

Commands to document **after** setup exists (not runnable promises for the current checkout):

```bash
cd backend
python -m pytest --collect-only --ds=config.test_settings
python -m pytest apps/core/tests apps/accounts/tests --ds=config.test_settings
# Add scoped --cov and --cov-branch once pytest-cov is installed/configured.

cd frontend
npm ci
npm test
npm run test:coverage
# npx playwright test once the proposed browser config/dependency is installed.
```

Final implementation report must include runtime versions, commands actually run, collected/passed/failed/skipped counts, scoped coverage, remaining issues and reasons for any test replacement. Never report "fully covered" solely because a file has many tests.

## 12. Approval checklist

Before implementation, confirm:

1. Registration scope includes verification and resend (recommended).
2. Cookie-based 201 success with null data remains the contract, or specify the intended body.
3. Duplicate-email error uses generic conflict or an email-specific code.
4. Token replay/resend invalidation and verification-cookie cleanup policies.
5. Permission to make narrowly scoped production fixes after regression tests reproduce the issues above; otherwise implementation stops at documented failures.
6. Adoption of a small Playwright browser layer and isolated CI/test settings in addition to existing pytest/Vitest tools.

**Recommended first implementation batch:** Phase 0 and the core response/error/validation suites. This establishes reusable trust before expanding registration workflow tests, and becomes the same foundation for login, password reset and checkout later.
