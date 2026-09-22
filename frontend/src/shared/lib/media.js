
const MEDIA_BASE_URL = import.meta.env.VITE_API_ORIGIN;

export const getMediaUrl = (path) => {
    if (!path) return null;
    
    if (path.startsWith('http')) {
        const url = new URL(path);
        return `${MEDIA_BASE_URL}${url.pathname}`;
    }
    
    return `${MEDIA_BASE_URL}${path}`;
};