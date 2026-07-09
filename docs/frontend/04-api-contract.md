# API Contract & Data Transformation

This document outlines how the BikeExpress frontend communicates with the Django backend. To prevent components from crashing due to unexpected data shapes or missing error fields, all API communication must pass through our transformation layer: `src/api/transformers.js`.

---

## 1. The Universal Backend Envelope

Every single response from the Django backend—whether it is a 200 OK success or a 400 Bad Request error—is guaranteed to be wrapped in this exact JSON structure:

```json
{
  "success": true,
  "message": "Human readable summary",
  "data": { ... },
  "errors": { ... },
  "meta": { "request_id": "uuid" }
}
```

Components and Hooks should **never** have to deal with this envelope. If you find yourself writing `response.data.data` in a component, you have bypassed the architecture.

---

## 2. Success Unwrapping (`extractResponse`)

When a backend call is successful, the `extractResponse` function strips away the envelope. 

### Rules for `extractResponse`:
* **Where to use it:** It must be called at the end of **every** function inside `src/services/*`.
* **What it does:** It returns exactly what the backend sent inside the `data`, `message`, and `meta` fields.
* **What it NEVER does:** It never renames keys, filters arrays, or transforms the internal shape of the data. That is the responsibility of the Hook or the Component.

**Example Service Usage:**
```javascript
// src/services/accountService.js
login: async (payload) => {
  const response = await api.post("/api/accounts/login/", payload);
  // Returns { data: { access, user }, message: "Login successful.", meta: null }
  return extractResponse(response); 
}
```

---

## 3. Error Normalization (`normalizeError`)

Axios throws errors in vastly different shapes depending on what went wrong (e.g., a network timeout looks entirely different from a 400 Validation Error). 

The `normalizeError` function takes *any* error and forces it into one predictable, bulletproof shape.

### The Guaranteed Error Shape:
Whenever you pass an error through `normalizeError`, you are guaranteed to get this object back:

```javascript
{
  message: "String",         // Always a string (derived from backend or HTTP status)
  errors: { ... } | null,    // The exact field errors from Django
  meta: { ... } | null,      // Meta info, like request_id
  status: 400,               // HTTP Status code (or null for network errors)
  requestId: "uuid" | null,  
  
  // Mechanical boolean flags for easy UI logic
  isNetworkError: false,
  isServerError: false,
  isClientError: true,       // 4xx errors
  isAuthError: false,        // 401
  isForbidden: false,        // 403
  isNotFound: false,         // 404
  isRateLimit: false         // 429
}
```

### Rules for `normalizeError`:
* **Where to use it:** It must be called inside your Hooks (`src/hooks/*`), usually inside the `onError` callback of a TanStack Mutation, or before setting UI error states.
* **Fallback Messages:** If the backend does not provide a `message`, the transformer will automatically derive a user-friendly one based on the status code (e.g., `500` $\rightarrow$ "Server error. Please try again later.").
* **Preserving Field Errors:** It passes the `errors` object through completely untouched. If Django sends `{ email: ["Invalid email"] }`, your form hook will receive exactly that.

---

## 4. The Data Flow Summary

To summarize the contract:

1. **Services Layer:** Uses `api.post/get` $\rightarrow$ Passes result through `extractResponse` $\rightarrow$ Returns clean data.
2. **Hooks Layer (Success):** Receives clean data $\rightarrow$ Updates Zustand or React Query.
3. **Hooks Layer (Error):** Catches Axios error $\rightarrow$ Passes through `normalizeError` $\rightarrow$ Extracts `formError` or `fieldErrors` for the UI.
4. **UI Layer:** Only ever deals with cleanly mapped `data` or string `errors`.