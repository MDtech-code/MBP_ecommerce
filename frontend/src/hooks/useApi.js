import { api } from "../api/client";

export const useApi = () => {

  const get = async (url, config = {}) => {
    const response = await api.get(url, config);
    return response.data; // ✅ return raw backend response
  };

  const post = async (url, payload = {}, config = {}) => {
    const response = await api.post(url, payload, config);
    return response.data; // ✅ same as fetch().json()
  };

  const put = async (url, payload = {}, config = {}) => {
    const response = await api.put(url, payload, config);
    return response.data;
  };

  const remove = async (url, config = {}) => {
    const response = await api.delete(url, config);
    return response.data;
  };

  const upload = async (url, formData) => {
    const response = await api.post(url, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  };

  return { get, post, put, remove, upload };
};
// import { api } from "../api/client";

// export const useApi = () => {

//   const handleResponse = (response) => {
//     const { success, data, message, errors } = response.data;

//     if (!success) {
//       throw {
//         message: message || "Request failed",
//         errors,
//       };
//     }

//     return data;
//   };

//   const get = async (url, config = {}) => {
//     const response = await api.get(url, config);
//     return handleResponse(response);
//   };

//   const post = async (url, payload = {}, config = {}) => {
//     const response = await api.post(url, payload, config);
//     return handleResponse(response);
//   };

//   const put = async (url, payload = {}, config = {}) => {
//     const response = await api.put(url, payload, config);
//     return handleResponse(response);
//   };

//   const remove = async (url, config = {}) => {
//     const response = await api.delete(url, config);
//     return handleResponse(response);
//   };

//   const upload = async (url, formData) => {
//     const response = await api.post(url, formData, {
//       headers: {
//         "Content-Type": "multipart/form-data",
//       },
//     });
//     return handleResponse(response);
//   };

//   return { get, post, put, remove,upload };
// };