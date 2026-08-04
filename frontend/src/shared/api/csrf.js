// src/shared/api/csrf.js
//
// Single source of truth for CSRF cookie bootstrapping.

//
// This module removes that coupling: ensureCsrfToken() is called once,
// unconditionally, on app load — before any form can be submitted —
// so every endpoint needing CSRF protection already has a token
// available, regardless of which page the user starts on.
import { api } from "./client";
import {getCookie} from "@shared/lib"

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

   if (getCookie("csrftoken")) {
    return Promise.resolve();
  }
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
