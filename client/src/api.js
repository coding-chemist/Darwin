import axios from 'axios';

// In dev, CRA proxy forwards to localhost:8000.
// In production (Vercel), set REACT_APP_API_URL to the HF Space URL.
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '',
});

export default api;
