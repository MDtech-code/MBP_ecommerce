import { clearAuth } from "./authToken";
export const initAuthSync = () => {
  const handler = (event) => {
    if (event.key !== "auth_event") return;
    try {
      const data = JSON.parse(event.newValue);
      if (data.type === "LOGOUT") {
        sessionStorage.setItem("logged_out", "true");
        clearAuth();
        window.location.href = "/login";
      }
      if (data.type === "LOGIN") {
        sessionStorage.removeItem("logged_out");
        window.location.href = "/";
        
      }
    } catch {
      // invalid JSON in storage — ignore
    }
  };

  window.addEventListener("storage", handler);

  // Return cleanup function — call this when app unmounts
  return () => window.removeEventListener("storage", handler);
};
// import { clearAuth } from "./authToken";

// export const initAuthSync = () => {

//     window.addEventListener("storage", (event) => {
//         if (event.key !== "auth_event") return;

//         try {
//             const data = JSON.parse(event.newValue)

//             if (data.type === "LOGOUT") {
//                 clearAuth()
//                 window.location.href = "/login"
//             }

//             if (data.type === "LOGIN") {
//                 // window.location.reload()
//                 window.location.href ='/'
//             }
//         } catch {
//             // invalid JSON in storage — ignore
//         }
//     });

// };
