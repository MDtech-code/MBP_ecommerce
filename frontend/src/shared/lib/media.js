import { API_BASE_URL } from "@shared/config";

export const getMediaUrl = (path) => {
  if (!path) return null;

  if (path.startsWith("http")) {
    const url = new URL(path);
    return `${API_BASE_URL}${url.pathname}`;
  }

  return `${API_BASE_URL}${path}`;
};
