import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  // IMPORTANT: send httpOnly cookies with every request
  withCredentials: true,
});

// No token management needed — httpOnly cookies are sent automatically.
// 401 handling is done in AuthProvider via interceptor setup.

export default api;
