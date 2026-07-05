// src/test/hooks/account/useBootstrapAuth.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

// ─────────────────────────────────────────────────────────────────────────────
// All mocks hoisted so vi.mock factories can reference them safely
// ─────────────────────────────────────────────────────────────────────────────

const {
  bootstrap,
  getProfile,
  setAuthToken,
  setUser,
  setBootstrapping,
} = vi.hoisted(() => ({
  bootstrap: vi.fn(),
  getProfile: vi.fn(),
  setAuthToken: vi.fn(),
  setUser: vi.fn(),
  setBootstrapping: vi.fn(),
}));

vi.mock("../../../services/accountService", () => ({
  accountService: {
    bootstrap,
    getProfile,
  },
}));

vi.mock("../../../api/auth", () => ({
  setAuthToken,
}));

// authState is mutated per-test before renderHook
let authState = { isAuthenticated: false };

vi.mock("../../../stores/authStore", () => ({
  useAuthStore: (selector) =>
    selector({
      isAuthenticated: authState.isAuthenticated,
      setUser,
      setBootstrapping,
    }),
}));

// ─────────────────────────────────────────────────────────────────────────────
// Reset between every test
// The critical fix: vi.resetModules() clears the module registry so the
// module-level `bootstrapAttempted` flag inside useBootstrapAuth.js
// is re-initialized to false for every single test.
// ─────────────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  vi.resetModules(); // ← resets bootstrapAttempted flag

  authState = { isAuthenticated: false };
  sessionStorage.clear();
});

// ─────────────────────────────────────────────────────────────────────────────
// Helper: dynamic import AFTER resetModules so each test gets a fresh module
// ─────────────────────────────────────────────────────────────────────────────

async function getHook() {
  const mod = await import(
    "../../../hooks/account/useBootstrapAuth"
  );
  return mod.useBootstrapAuth;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("useBootstrapAuth", () => {
  it("restores access token and user profile", async () => {
    bootstrap.mockResolvedValue({
      data: { access: "new-access-token" },
    });

    getProfile.mockResolvedValue({
      data: { id: 1, email: "john@test.com" },
    });

    const useBootstrapAuth = await getHook();
    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(bootstrap).toHaveBeenCalledTimes(1);
    });

    expect(setAuthToken).toHaveBeenCalledWith(
      "new-access-token",
    );
    expect(getProfile).toHaveBeenCalledTimes(1);
    expect(setUser).toHaveBeenCalledWith({
      id: 1,
      email: "john@test.com",
    });
    expect(setBootstrapping).toHaveBeenLastCalledWith(
      false,
    );
  });

  it("does not fetch profile when refresh returns no access token", async () => {
    bootstrap.mockResolvedValue({ data: {} });

    const useBootstrapAuth = await getHook();
    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(bootstrap).toHaveBeenCalled();
    });

    expect(getProfile).not.toHaveBeenCalled();
    expect(setUser).not.toHaveBeenCalled();
    expect(setBootstrapping).toHaveBeenCalledWith(false);
  });

  it("finishes silently when refresh request fails", async () => {
    bootstrap.mockRejectedValue(
      new Error("Refresh failed"),
    );

    const useBootstrapAuth = await getHook();
    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(bootstrap).toHaveBeenCalled();
    });

    expect(getProfile).not.toHaveBeenCalled();
    expect(setUser).not.toHaveBeenCalled();
    expect(setBootstrapping).toHaveBeenLastCalledWith(
      false,
    );
  });

  it("skips bootstrap when already authenticated", async () => {
    authState.isAuthenticated = true;

    const useBootstrapAuth = await getHook();
    renderHook(() => useBootstrapAuth());

    // No async needed — effect runs synchronously for this branch
    expect(bootstrap).not.toHaveBeenCalled();
    expect(getProfile).not.toHaveBeenCalled();
    expect(setBootstrapping).toHaveBeenCalledWith(false);
  });

  it("skips bootstrap after explicit logout", async () => {
    sessionStorage.setItem("logged_out", "true");

    const useBootstrapAuth = await getHook();
    renderHook(() => useBootstrapAuth());

    expect(bootstrap).not.toHaveBeenCalled();
    expect(getProfile).not.toHaveBeenCalled();
    expect(setBootstrapping).toHaveBeenCalledWith(false);
  });

  it("stores restored profile after successful bootstrap", async () => {
    const profile = {
      id: 7,
      email: "alice@test.com",
      profile: { phone: "03001234567" },
    };

    bootstrap.mockResolvedValue({
      data: { access: "jwt-token" },
    });

    getProfile.mockResolvedValue({ data: profile });

    const useBootstrapAuth = await getHook();
    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(setUser).toHaveBeenCalled();
    });

    expect(setUser).toHaveBeenCalledWith(profile);
  });

  it("always ends bootstrapping after successful restore", async () => {
    bootstrap.mockResolvedValue({
      data: { access: "token" },
    });

    getProfile.mockResolvedValue({
      data: { id: 1 },
    });

    const useBootstrapAuth = await getHook();
    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(
        setBootstrapping,
      ).toHaveBeenLastCalledWith(false);
    });
  });

  it("always ends bootstrapping after failed restore", async () => {
    bootstrap.mockRejectedValue(
      new Error("Network Error"),
    );

    const useBootstrapAuth = await getHook();
    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(
        setBootstrapping,
      ).toHaveBeenLastCalledWith(false);
    });
  });
});
// // src/test/hooks/account/useBootstrapAuth.test.jsx

// import { describe, it, expect, vi, beforeEach } from "vitest";
// import { renderHook, waitFor } from "@testing-library/react";


// // ─────────────────────────────────────────────────────────────────────────────
// // ALL hoisted mocks must come before imports that trigger module resolution
// // Use vi.hoisted for everything that vi.mock factories reference
// // ─────────────────────────────────────────────────────────────────────────────

// const {
//   bootstrap,
//   getProfile,
//   setAuthToken,
//   setUser,
//   setBootstrapping,
// } = vi.hoisted(() => ({
//   bootstrap: vi.fn(),
//   getProfile: vi.fn(),
//   setAuthToken: vi.fn(),
//   setUser: vi.fn(),
//   setBootstrapping: vi.fn(),
// }));



// // ─────────────────────────────────────────────────────────────────────────────
// // Mocks — factories only reference hoisted vars (safe)
// // ─────────────────────────────────────────────────────────────────────────────

// vi.mock("../../../services/accountService", () => ({
//   accountService: {
//     bootstrap,
//     getProfile,
//   },
// }));

// vi.mock("../../../api/auth", () => ({
//   setAuthToken,
// }));

// let authState = { isAuthenticated: false };

// vi.mock("../../../stores/authStore", () => ({
//   useAuthStore: (selector) =>
//     selector({
//       isAuthenticated: authState.isAuthenticated,
//       setUser,
//       setBootstrapping,
//     }),
// }));

// // ─────────────────────────────────────────────────────────────────────────────
// // Import AFTER mocks are registered
// // ─────────────────────────────────────────────────────────────────────────────

// import { useBootstrapAuth } from "../../../hooks/account/useBootstrapAuth";

// // // ─────────────────────────────────────────────────────────────────────────────
// // // Shared mocks
// // // ─────────────────────────────────────────────────────────────────────────────

// // // const bootstrap = vi.fn();
// // // const getProfile = vi.fn();
// // const {
// //   bootstrap,
// //   getProfile,
// // } = vi.hoisted(() => ({
// //   bootstrap: vi.fn(),
// //   getProfile: vi.fn(),
// // }));

// // const setUser = vi.fn();
// // const setBootstrapping = vi.fn();

// // let authState = {
// //   isAuthenticated: false,
// // };

// // const setAuthToken = vi.fn();

// // vi.mock("../../../services/accountService", () => ({
// //   accountService: {
// //     bootstrap,
// //     getProfile,
// //   },
// // }));

// // vi.mock("../../../api/auth", () => ({
// //   setAuthToken,
// // }));

// // vi.mock("../../../stores/authStore", () => ({
// //   useAuthStore: (selector) =>
// //     selector({
// //       isAuthenticated: authState.isAuthenticated,
// //       setUser,
// //       setBootstrapping,
// //     }),
// // }));

// // ─────────────────────────────────────────────────────────────────────────────
// // Reset
// // ─────────────────────────────────────────────────────────────────────────────

// beforeEach(() => {
//   vi.clearAllMocks();

//   authState = {
//     isAuthenticated: false,
//   };

//   sessionStorage.clear();
// });

// // ─────────────────────────────────────────────────────────────────────────────
// // Tests
// // ─────────────────────────────────────────────────────────────────────────────

// describe("useBootstrapAuth", () => {
//   it("restores access token and user profile", async () => {
//     bootstrap.mockResolvedValue({
//       data: {
//         access: "new-access-token",
//       },
//     });

//     getProfile.mockResolvedValue({
//       data: {
//         id: 1,
//         email: "john@test.com",
//       },
//     });

//     renderHook(() => useBootstrapAuth());

//     await waitFor(() => {
//       expect(bootstrap).toHaveBeenCalledTimes(1);
//     });

//     expect(setAuthToken).toHaveBeenCalledWith(
//       "new-access-token"
//     );

//     expect(getProfile).toHaveBeenCalledTimes(1);

//     expect(setUser).toHaveBeenCalledWith({
//       id: 1,
//       email: "john@test.com",
//     });

//     expect(setBootstrapping).toHaveBeenLastCalledWith(
//       false
//     );
//   });

//   it("does not fetch profile when refresh returns no access token", async () => {
//     bootstrap.mockResolvedValue({
//       data: {},
//     });

//     renderHook(() => useBootstrapAuth());

//     await waitFor(() => {
//       expect(bootstrap).toHaveBeenCalled();
//     });

//     expect(getProfile).not.toHaveBeenCalled();

//     expect(setUser).not.toHaveBeenCalled();

//     expect(setBootstrapping).toHaveBeenCalledWith(
//       false
//     );
//   });

//   it("finishes silently when refresh request fails", async () => {
//     bootstrap.mockRejectedValue(
//       new Error("Refresh failed")
//     );

//     renderHook(() => useBootstrapAuth());

//     await waitFor(() => {
//       expect(bootstrap).toHaveBeenCalled();
//     });

//     expect(getProfile).not.toHaveBeenCalled();

//     expect(setUser).not.toHaveBeenCalled();

//     expect(setBootstrapping).toHaveBeenLastCalledWith(
//       false
//     );
//   });

//   it("skips bootstrap when already authenticated", async () => {
//     authState.isAuthenticated = true;

//     renderHook(() => useBootstrapAuth());

//     expect(bootstrap).not.toHaveBeenCalled();

//     expect(getProfile).not.toHaveBeenCalled();

//     expect(setBootstrapping).toHaveBeenCalledWith(
//       false
//     );
//   });

//   it("skips bootstrap after explicit logout", () => {
//     sessionStorage.setItem("logged_out", "true");

//     renderHook(() => useBootstrapAuth());

//     expect(bootstrap).not.toHaveBeenCalled();

//     expect(getProfile).not.toHaveBeenCalled();

//     expect(setBootstrapping).toHaveBeenCalledWith(
//       false
//     );
//   });

//   it("stores restored profile after successful bootstrap", async () => {
//     const profile = {
//       id: 7,
//       email: "alice@test.com",
//       profile: {
//         phone: "03001234567",
//       },
//     };

//     bootstrap.mockResolvedValue({
//       data: {
//         access: "jwt-token",
//       },
//     });

//     getProfile.mockResolvedValue({
//       data: profile,
//     });

//     renderHook(() => useBootstrapAuth());

//     await waitFor(() => {
//       expect(setUser).toHaveBeenCalled();
//     });

//     expect(setUser).toHaveBeenCalledWith(profile);
//   });

//   it("always ends bootstrapping after successful restore", async () => {
//     bootstrap.mockResolvedValue({
//       data: {
//         access: "token",
//       },
//     });

//     getProfile.mockResolvedValue({
//       data: {
//         id: 1,
//       },
//     });

//     renderHook(() => useBootstrapAuth());

//     await waitFor(() => {
//       expect(setBootstrapping).toHaveBeenLastCalledWith(
//         false
//       );
//     });
//   });

//   it("always ends bootstrapping after failed restore", async () => {
//     bootstrap.mockRejectedValue(
//       new Error("Network Error")
//     );

//     renderHook(() => useBootstrapAuth());

//     await waitFor(() => {
//       expect(setBootstrapping).toHaveBeenLastCalledWith(
//         false
//       );
//     });
//   });
// });