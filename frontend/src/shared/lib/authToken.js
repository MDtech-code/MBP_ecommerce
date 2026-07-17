// src/api/authToken.js

import { api } from "@shared/api";

let accessToken = null;

export const setAuthToken = (token) => {
    accessToken = token;

    if (token) {
        api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    } else {
        delete api.defaults.headers.common["Authorization"];
    }
};

export const getAuthToken = () => accessToken;
export const hasAuthToken = () => !!accessToken

export const clearAuth = () => {
    accessToken = null;
    delete api.defaults.headers.common["Authorization"];
};

export const broadcastLogin = () => {
    localStorage.setItem("auth_event", JSON.stringify({
        type: "LOGIN",
        time: Date.now()
    }));
};

export const broadcastLogout = () => {
    localStorage.setItem("auth_event", JSON.stringify({
        type: "LOGOUT",
        time: Date.now()
    }));
};