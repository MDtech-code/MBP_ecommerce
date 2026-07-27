// // src/shared/lib/media.js
// /**
//  * Converts a relative media path from Django backend to full URL.
//  * Django serves media files from its own origin, not the Vite dev server.
//  *
//  * "/media/avatars/file.jpg" → "https://localhost:8000/media/avatars/file.jpg"
//  * null or "" → null (let component show fallback)
//  */
// export const getMediaUrl = (path) => {
//   if (!path) return null;
//   if (path.startsWith("http")) return path; // already full URL
//   return `${import.meta.env.VITE_API_ORIGIN}${path}`;
// };
// src/shared/lib/media.js

// Browser always uses localhost - never Docker internal hostnames
const MEDIA_BASE_URL = 'https://localhost:8000';

export const getMediaUrl = (path) => {
    if (!path) return null;
    
    if (path.startsWith('http')) {
        // Replace any hostname with localhost for browser access
        const url = new URL(path);
        return `${MEDIA_BASE_URL}${url.pathname}`;
    }
    
    return `${MEDIA_BASE_URL}${path}`;
};