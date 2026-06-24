import axios from 'axios';

export const api = axios.create({
    baseURL: import.meta.env.VITE_API_ORIGIN,
    // withCredentials: true,
});
// Attach access token from memory
export const setAuthToken = (token) => {
    if (token) {
        api.defaults.headers.Authorization = `Bearer ${token}`;
    } else {
        delete api.defaults.headers.Authorization;
    }
};

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });

    failedQueue = [];
};

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {

            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                })
                    .then((token) => {
                        originalRequest.headers.Authorization = `Bearer ${token}`;
                        return api(originalRequest);
                    })
                    .catch((err) => Promise.reject(err));
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                const response = await axios.post(
                    `${import.meta.env.VITE_API_BASE_URL}/token/refresh/`,
                    {},
                    { withCredentials: true }
                );

                const newAccess = response.data.data.access;

                setAuthToken(newAccess);
                processQueue(null, newAccess);

                return api(originalRequest);
            } catch (err) {
                //setAuthToken(null);     // Clear access
                //window.location.href = "/login";
                processQueue(err, null);
                return Promise.reject(err);
            } finally {
                isRefreshing = false;
            }
        }
        //rate limit
        if (error.response?.status === 429) {
            alert("Too many requests. Please slow down.");
            return Promise.reject(error);
        }


        return Promise.reject(error);
    }
);
    
/*
// Attach CSRF from cookie
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

api.interceptors.request.use((config) => {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken;
    }
    return config;
});
*/

/*
Role-based frontend route protection?
✅ Automatic logout on refresh failure?
✅ React Query integration?
✅ Multi-tab token synchronization?
React Query
File uploads
WebSockets
GraphQL
Multi-tenant headers
Request tracing headers
Rate limit handling
 */