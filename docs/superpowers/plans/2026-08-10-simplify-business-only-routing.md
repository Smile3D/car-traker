# Simplify Routing: Business-Only Login/Register, Hide Garage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Login and registration always lead to the business account (CRM); the personal "garage" expense tracker disappears from all navigation and UI, but its code stays in the repo, reachable only by direct URL — which now redirects instead of rendering.

**Architecture:** Remove the now-dead `?type=business` branching from `register.vue` (the branch was small: one checkbox, one heading condition, one computed). Collapse `getPostAuthRedirectPath()` to a constant `/crm` since the only caller-supplied input (`company_id`) no longer changes the outcome. Give the two garage pages a new guard middleware that redirects instead of rendering, replacing their current `auth` middleware (auth's "not logged in → /login" behavior is preserved, layered with a new "logged in → /crm" branch). Point the one remaining `/garage` fallback (`business.ts`, guarding all `/crm/*` pages for users with no `company_id`) at `/settings` instead, since redirecting it to `/garage` would now bounce straight back to `/crm` in an infinite loop.

**Tech Stack:** Nuxt 4 (Vue 3, `<script setup>`, TypeScript), Pinia, `@nuxtjs/i18n`, file-based routing with `definePageMeta`.

## Global Constraints

- Do not delete any file under `pages/garage/`, `middleware/business.ts`, `layouts/landing.vue`, or any other existing file — only edit routing/redirect logic. The garage feature must remain restorable by reverting a middleware assignment.
- `frontend/app/utils/authRedirect.ts` and its 3 call sites (`pages/login.vue`, `pages/register.vue`, `pages/auth/confirm-email.vue`) are the only places that decide "where does the user land after auth" — confirmed by repo-wide grep for `getPostAuthRedirectPath`.
- No test runner exists in this repo (`frontend/package.json` has no `test`/`lint`/`typecheck` script). Verification is manual: run `npm run dev` and click through the flows described in each task's Verify step.
- Follow existing code conventions in the touched files: `<script setup lang="ts">`, full descriptive names, no abbreviations (per user's global CLAUDE.md).

---

## Investigation Summary (already done — do not repeat)

- `frontend/app/pages/login.vue` has **no** `?type=business` branching at all — it already always performs the business login flow. Only its redirect call needs updating (Task 1).
- `frontend/app/pages/register.vue` has a small branch: `isForcedBusiness` (computed from `route.query.type === 'business'`), `isBusinessAccount` (ref, defaults to `isForcedBusiness`), a checkbox bound to it, and a conditional heading. This is the branch to remove (Task 2).
- `frontend/app/utils/authRedirect.ts` is a 3-line function: `companyId != null ? '/crm' : '/garage'`. This is the only place deciding post-login/register/confirm-email destination (Task 1).
- No links to `/garage` exist anywhere in navigation, headers, sidebars, or the landing page (`for-dealers.vue` + its `landing/*` components). The only `/garage` references outside `pages/garage/*` itself are: `middleware/business.ts` (fallback for users with no `company_id`) and `utils/authRedirect.ts` (Task 1 removes this one). Confirmed by repo-wide grep — so Step 2.1/2.2 of the original request ("remove garage links from nav/landing") requires **no file changes**; there is nothing to remove.
- There is no separate "personal garage" marketing landing page — `for-dealers.vue` (layout `landing`) is the only landing page in the app, and it never mentions garage/personal use. Step 2.2 of the original request requires **no file changes**.
- `layouts/landing.vue` belongs to the business landing (`for-dealers.vue`), not to garage. `pages/garage/index.vue` and `pages/garage/[id].vue` use no `layout:` at all (they fall back to `layouts/default.vue`, a generic authenticated shell with no garage links). There is no garage-specific layout to disable.
- The 4 internal landing CTAs (`LandingHeader.vue`, `LandingCta.vue`, `LandingPricing.vue`, `LandingStickyMobileCta.vue`) already link to `/register?type=business`. Left untouched, they keep working after Task 2 (the query param becomes a harmless no-op). Not part of this plan — flagged as a question for the user at the end (see plan's closing note).
- Backend (`backend/app/routers/auth.py`): registering with `account_type: "business"` creates a `Company` row and sets `company_id` immediately (line ~167). So after Task 2, every new registration (except invited employees, whose `company_id` comes from the invite) has `company_id` set from the start — `company_id === null` becomes a legacy-only state for accounts created before this change.
- `middleware/business.ts` guards all 11 `/crm/*` pages (verified by grep) and currently sends users with no `company_id` to `/garage`. Since Task 3 makes `/garage` itself redirect authenticated users to `/crm`, leaving this as `/garage` would create an infinite redirect loop for any legacy no-company account. Task 4 repoints it to `/settings`, which already renders safely for users with no `company_id` (`settings.vue` only shows the profile section in that case — confirmed by reading the file).

---

### Task 1: Collapse `getPostAuthRedirectPath` to always return `/crm`

**Files:**
- Modify: `frontend/app/utils/authRedirect.ts`
- Modify: `frontend/app/pages/login.vue:30`
- Modify: `frontend/app/pages/register.vue:65`
- Modify: `frontend/app/pages/auth/confirm-email.vue:31`

**Interfaces:**
- Produces: `getPostAuthRedirectPath(): string` — no parameters, always returns `'/crm'`. Later tasks don't depend on this, but every existing call site changes from `getPostAuthRedirectPath(authStore.user?.company_id)` to `getPostAuthRedirectPath()`.

- [ ] **Step 1: Simplify the function**

Replace the full contents of `frontend/app/utils/authRedirect.ts`:

```ts
export function getPostAuthRedirectPath(): string {
  return '/crm'
}
```

- [ ] **Step 2: Update the three call sites**

In `frontend/app/pages/login.vue`, change line 30:

```ts
router.push(getPostAuthRedirectPath())
```

In `frontend/app/pages/register.vue`, change line 65 (inside the `else` branch of the `requiresEmailConfirmation` check):

```ts
router.push(inviteToken.value ? '/settings' : getPostAuthRedirectPath())
```

In `frontend/app/pages/auth/confirm-email.vue`, change line 31:

```ts
router.push(getPostAuthRedirectPath())
```

- [ ] **Step 3: Verify no other caller was missed**

Run: `grep -rn "getPostAuthRedirectPath" frontend/app`
Expected: exactly 4 matches — the definition plus the 3 updated call sites, all passing no arguments except the definition.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/utils/authRedirect.ts frontend/app/pages/login.vue frontend/app/pages/register.vue frontend/app/pages/auth/confirm-email.vue
git commit -m "Always route post-auth to the business dashboard, not garage"
```

---

### Task 2: Remove the personal/individual branch from `register.vue`

**Files:**
- Modify: `frontend/app/pages/register.vue`

**Interfaces:**
- Consumes: `getPostAuthRedirectPath()` from Task 1 (no arguments).
- Produces: none consumed by later tasks.

**Context:** Currently `register.vue` has:
- `isForcedBusiness = computed(() => route.query.type === 'business' && !inviteToken.value)`
- `isBusinessAccount = ref(isForcedBusiness.value)`
- A heading shown only `v-if="isForcedBusiness"`
- A checkbox `v-if="!isForcedBusiness && !inviteToken"` bound to `isBusinessAccount`
- `authStore.register(..., isBusinessAccount.value ? 'business' : 'individual', ...)`

After this task, registration is always `'business'` (the invite flow already ignores whatever `account_type` is sent server-side — confirmed in `backend/app/routers/auth.py` line ~150 — so sending `'business'` unconditionally is safe even when `inviteToken.value` is set). The heading shows unconditionally instead of only when forced.

- [ ] **Step 1: Remove the two reactive declarations**

In `frontend/app/pages/register.vue`, delete these lines (currently lines 35–38):

```ts
// An invite fully determines company/role — the business-account checkbox
// only matters when registering without one.
const isForcedBusiness = computed<boolean>(() => route.query.type === 'business' && !inviteToken.value)
const isBusinessAccount = ref(isForcedBusiness.value)
```

- [ ] **Step 2: Update the register() call**

Change line 53 from:

```ts
isBusinessAccount.value ? 'business' : 'individual',
```

to:

```ts
'business',
```

- [ ] **Step 3: Make the heading unconditional**

Change the template (currently line 78–80) from:

```html
<h2 v-if="isForcedBusiness" class="mb-4 text-center text-lg font-semibold text-foreground">
  {{ t('auth.register.businessHeading') }}
</h2>
```

to:

```html
<h2 class="mb-4 text-center text-lg font-semibold text-foreground">
  {{ t('auth.register.businessHeading') }}
</h2>
```

- [ ] **Step 4: Delete the checkbox block**

Remove this whole block (currently lines 135–144):

```html
<!-- BusinessAccountCheckbox: hidden entirely when joining via invite —
     company/role are already fully determined by the invite token. -->
<label v-if="!isForcedBusiness && !inviteToken" class="flex items-center gap-2 text-sm text-foreground">
  <input
    v-model="isBusinessAccount"
    type="checkbox"
    class="size-4 rounded border-border text-primary focus:ring-1 focus:ring-primary"
  >
  {{ t('auth.register.businessCheckbox') }}
</label>
```

- [ ] **Step 5: Check for now-unused imports/locale keys**

Run: `grep -n "isForcedBusiness\|isBusinessAccount\|businessCheckbox" frontend/app/pages/register.vue`
Expected: no matches. (The locale key `auth.register.businessCheckbox` in `frontend/locales/uk.json` / `ru.json` becomes unused — leave the locale files alone; `check:i18n` only checks for missing keys, not unused ones, so this is not a build/lint failure. Do not delete the locale key — it documents the disabled feature, consistent with "disable, don't delete.")

- [ ] **Step 6: Manual verification**

Run: `cd frontend && npm run dev`
Open `http://localhost:3000/register` (no query params) in a browser.
Expected: the business heading ("Реєстрація для авто-майданчиків") shows immediately, no checkbox is present, and submitting creates a business account (verify via the network tab: POST `/auth/register` body has `"account_type":"business"`).

Then open `http://localhost:3000/register?type=business` and confirm it renders identically (the query param is now a no-op).

- [ ] **Step 7: Commit**

```bash
git add frontend/app/pages/register.vue
git commit -m "Make business registration the only registration flow"
```

---

### Task 3: Redirect direct garage URLs instead of rendering them

**Files:**
- Create: `frontend/app/middleware/garage-disabled.ts`
- Modify: `frontend/app/pages/garage/index.vue:4`
- Modify: `frontend/app/pages/garage/[id].vue:19`

**Interfaces:**
- Consumes: `useAuthStore().isAuthenticated` (existing getter, `frontend/app/stores/auth.ts:13`, `computed(() => Boolean(token.value))`).
- Produces: a Nuxt route middleware named `garage-disabled`, referenced by name (Nuxt auto-registers middleware files in `app/middleware/` by filename) from `definePageMeta({ middleware: 'garage-disabled' })`.

**Context:** Both garage pages currently declare `definePageMeta({ middleware: 'auth' })`. The `auth` middleware (`frontend/app/middleware/auth.ts`) redirects unauthenticated users to `/login` and otherwise lets the page render. The new `garage-disabled` middleware replaces `auth` on these two pages: it keeps the "not logged in → `/login`" behavior, but additionally redirects logged-in users to `/crm` instead of letting the garage page render. This satisfies "don't delete the page, but any direct URL hit redirects" without touching the page components themselves.

- [ ] **Step 1: Create the middleware**

Create `frontend/app/middleware/garage-disabled.ts`:

```ts
export default defineNuxtRouteMiddleware(() => {
  const authStore = useAuthStore()

  if (!authStore.isAuthenticated) {
    return navigateTo('/login')
  }

  return navigateTo('/crm')
})
```

- [ ] **Step 2: Wire it into both garage pages**

In `frontend/app/pages/garage/index.vue`, change line 4 from:

```ts
definePageMeta({ middleware: 'auth' })
```

to:

```ts
definePageMeta({ middleware: 'garage-disabled' })
```

In `frontend/app/pages/garage/[id].vue`, change line 19 the same way:

```ts
definePageMeta({ middleware: 'garage-disabled' })
```

- [ ] **Step 3: Manual verification — logged out**

Run: `cd frontend && npm run dev`
Log out (or open an incognito window), then navigate directly to `http://localhost:3000/garage`.
Expected: redirected to `/login`, garage UI never flashes.

- [ ] **Step 4: Manual verification — logged in**

Log in with an existing account, then navigate directly to `http://localhost:3000/garage` and to `http://localhost:3000/garage/1`.
Expected: both redirect to `/crm`, garage UI never flashes.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/middleware/garage-disabled.ts frontend/app/pages/garage/index.vue "frontend/app/pages/garage/[id].vue"
git commit -m "Redirect direct garage URLs instead of rendering the garage UI"
```

---

### Task 4: Stop `business.ts` middleware from falling back to garage

**Files:**
- Modify: `frontend/app/middleware/business.ts`

**Interfaces:**
- Consumes: none new.
- Produces: none consumed by later tasks.

**Context:** `business.ts` guards all 11 `/crm/*` pages. It currently sends any authenticated user with no `company_id` to `/garage`. After Task 3, `/garage` immediately bounces any authenticated user back to `/crm`, which `business.ts` would again reject — an infinite redirect loop for the (now legacy-only) case of an account with no `company_id`. Point it at `/settings` instead: `settings.vue` already handles a missing `company_id` gracefully (it only renders the profile section, per the file's own `isCompanyMember` check), so this is a safe, working destination, not a dead end.

- [ ] **Step 1: Update the fallback path**

Change `frontend/app/middleware/business.ts` from:

```ts
export default defineNuxtRouteMiddleware(() => {
  const authStore = useAuthStore()

  if (!authStore.user?.company_id) {
    return navigateTo('/garage')
  }
})
```

to:

```ts
export default defineNuxtRouteMiddleware(() => {
  const authStore = useAuthStore()

  if (!authStore.user?.company_id) {
    return navigateTo('/settings')
  }
})
```

- [ ] **Step 2: Manual verification**

This path only triggers for an account with `company_id === null`, which (after Task 2) can no longer be created via normal registration. If a pre-existing test account with no `company_id` is available, log in with it, navigate to `http://localhost:3000/crm`, and confirm it lands on `/settings` (showing only the profile section) rather than looping or hitting `/garage`. If no such account exists, skip this manual check — note it as untested in the final report.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/middleware/business.ts
git commit -m "Send company-less accounts to settings instead of the disabled garage"
```

---

### Task 5: Full walkthrough per the original request's Step 3

**Files:** none (verification only, no code changes)

- [ ] **Step 1: Fresh registration**

Run: `cd frontend && npm run dev` (and ensure the backend is running per this repo's usual dev setup).
Open `http://localhost:3000/register` with no query parameters.
Expected: business registration form shows immediately (heading present, no checkbox), per Task 2's Step 6.

- [ ] **Step 2: Existing account login**

Log in with an existing test account (e.g. `aleksandrov+1@gmail.com`, if its password is available).
Expected: redirected to `/crm` (the CRM dashboard), not `/garage`, per Task 1.

- [ ] **Step 3: Direct garage URL**

With the same session still logged in, navigate to `http://localhost:3000/garage` and `http://localhost:3000/garage/1`.
Expected: both immediately redirect to `/crm`, per Task 3.

- [ ] **Step 4: Nav/landing sweep**

Open `http://localhost:3000/for-dealers` and check the header, hero, footer, and every CTA button.
Expected: no link or button anywhere mentions or points to garage — confirmed by the Investigation Summary's grep, but re-check visually since this is the request's own acceptance criterion.

No commit for this task — it is a verification pass. If any step fails, stop and re-open the relevant earlier task.

---

## Closing Note (report to the user, do not act on unilaterally)

After all 5 tasks are done and verified, tell the user:

> The `/register?type=business` URL used for prior outreach/marketing still works unchanged — the query param is now a harmless no-op since business is the only registration flow. Nothing needs to change there unless you'd like the URL simplified to plain `/register` for cleanliness (purely cosmetic, your call). Separately, the 4 internal landing CTAs (`LandingHeader.vue`, `LandingCta.vue`, `LandingPricing.vue`, `LandingStickyMobileCta.vue`) still link to `/register?type=business` too — same story, safe to leave or simplify.
