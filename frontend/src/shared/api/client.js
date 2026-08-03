// src/shared/api/client.js
import axios from "axios"


const config={
  baseURL:'',
  headers: {
    "Content-Type": "application/json",
  },
}
export const api = axios.create(config)
