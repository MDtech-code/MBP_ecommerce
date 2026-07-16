// // src/utils/media.js
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
