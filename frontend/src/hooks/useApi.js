import { api } from "../api/client";

export const useApi = () => {

  const get = async (url, config = {}) => {
    const response = await api.get(url, config);
    return response.data;
  };

  const post = async (url, payload = {}, config = {}) => {
    const response = await api.post(url, payload, config);
    return response.data;
  };

  const put = async (url, payload = {}, config = {}) => {
    const response = await api.put(url, payload, config);
    return response.data;
  };

  const remove = async (url, config = {}) => {
    const response = await api.delete(url, config);
    return response.data;
  };

  const upload = async (url, formData,onProgress) => {
    const response = await api.post(url, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: onProgress
        ? (e) => onProgress(Math.round((e.loaded * 100) / e.total))
        : undefined,
    });
    return response.data;
  };

  return { get, post, put, remove, upload };
};
