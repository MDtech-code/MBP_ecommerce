import { API_BASE_URL } from "@shared/config";

export const getMediaUrl = (path) => {
  if (!path) return null;

  if (path.startsWith("http")) {
    const url = new URL(path);
    const resolved = `${API_BASE_URL}${url.pathname}`;
    if (import.meta.env.DEV) {
      console.debug("[Media] Resolved absolute path:", { path, resolved });
    }
    return resolved;
  }

  const resolved = `${API_BASE_URL}${path}`;
  if (import.meta.env.DEV) {
    console.debug("[Media] Resolved relative path:", { path, resolved });
  }
  return resolved;
};
