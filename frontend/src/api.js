import axios from 'axios';

export const api = axios.create({ baseURL: '/api' });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function fetchAll(path, params = {}) {
  const results = [];
  let page = 1;
  let hasNext = true;
  while (hasNext) {
    const { data } = await api.get(path, { params: { ...params, page } });
    if (Array.isArray(data)) return data;
    results.push(...data.results);
    hasNext = Boolean(data.next);
    page += 1;
  }
  return results;
}
