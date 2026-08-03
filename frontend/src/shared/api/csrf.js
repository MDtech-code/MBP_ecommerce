// src/shared/api/csrf.js
//
// Single source of truth for CSRF cookie bootstrapping.
//
// Previously, individual views (RegisterView) set the csrftoken cookie
// as a side effect of an unrelated business action. That created a
// hidden dependency: any endpoint needing CSRF protection only worked
// if the user happened to hit register first, in the same browser
// session, with cookies intact. A user landing directly on
// /forgot-password with no prior visit had no token to send.
//
// This module removes that coupling: ensureCsrfToken() is called once,
// unconditionally, on app load — before any form can be submitted —
// so every endpoint needing CSRF protection already has a token
// available, regardless of which page the user starts on.
import { api } from "./client";

let csrfBootstrapPromise = null;

/**
 * Ensures a csrftoken cookie exists in the browser.
 *
 * Safe to call multiple times — the underlying request only fires once
 * per app session; subsequent calls return the same in-flight or
 * already-resolved promise, so mounting this in more than one place
 * (e.g. both a root App effect and a route guard) can't cause duplicate
 * network calls.
 *
 * @returns {Promise<void>}
 */
export const ensureCsrfToken = () => {
  console.log(csrfBootstrapPromise, "sirf andar aya hu")
  if (!csrfBootstrapPromise) {
    csrfBootstrapPromise = api
      .get("/api/csrf/", { withCredentials: true })
      .catch((err) => {
        // Reset so a later call can retry — a failed bootstrap (e.g.
        // backend down on first load) should not permanently block
        // every future attempt for the lifetime of the tab.
        csrfBootstrapPromise = null;
        throw err;
      });
  }
  return csrfBootstrapPromise;
};