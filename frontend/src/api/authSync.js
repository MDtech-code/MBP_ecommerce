import { clearAuth } from "./auth";

export const initAuthSync = () => {

    window.addEventListener("storage", (event) => {
        if (event.key !== "auth_event") return;

        const data = JSON.parse(event.newValue);

        if (data.type === "LOGOUT") {
            clearAuth();
            window.location.href = "/login";
        }

        if (data.type === "LOGIN") {
            // Optional: force reload to fetch new access token
            window.location.reload();
        }
    });

};