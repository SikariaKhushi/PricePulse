import axios from "axios";
const API_BASE = "http://localhost:8000"; // Change to your backend URL

export const trackProduct = (data) => axios.post(`${API_BASE}/products/track`, data);
export const getProduct = (id) => axios.get(`${API_BASE}/products/${id}`);
export const getPriceHistory = (id) => axios.get(`${API_BASE}/products/${id}/history`);
export const getComparisons = (id) => axios.get(`${API_BASE}/products/${id}/comparison`);
export const setAlert = (data) => axios.post(`${API_BASE}/alerts/`, data);
