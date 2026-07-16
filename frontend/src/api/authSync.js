// import { clearAuth } from "./auth";

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
//                 window.location.reload()
//             }
//         } catch {
//             // invalid JSON in storage — ignore
//         }
//     });

// };