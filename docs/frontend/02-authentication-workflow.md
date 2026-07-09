# Authentication Workflow

This document details the security model, token lifetime management, and synchronization mechanisms used across the BikeExpress frontend.

---

## Token Architecture & Storage

To protect user sessions from Cross-Site Scripting (XSS) attacks, we do **not** store JWT access tokens in `localStorage` or `sessionStorage`. 

1. **Access Token (Short-lived):** Stored strictly in raw JavaScript memory within `src/api/auth.js`. It is lost on page refresh.
2. **Refresh Token (Long-lived):** Managed by the Django backend using secure, `HttpOnly`, `SameSite=Lax` cookies. The frontend cannot read this token via JavaScript, protecting it from theft.

---

## The Silent Refresh & 401 Queue Mechanism

Because access tokens are short-lived and stored in memory, they expire frequently (and vanish on page reloads). The system uses an **Axios Interceptor Queue** in `src/api/interceptors.js` to handle token expiration completely seamlessly behind the scenes.

### Workflow Lifecycle