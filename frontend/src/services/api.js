const apiBase = 'http://localhost:8000';

export const api = {
  syncPosts(items){
    return axios.post(`${apiBase}/api/posts/bulk`, { items });
  },
  syncBrowse(items){
    return axios.post(`${apiBase}/api/browse-log`, { items });
  },
  listPosts(params){
    return axios.get(`${apiBase}/api/posts`, { params });
  },
  listBrowse(params){
    return axios.get(`${apiBase}/api/browse-log`, { params });
  }
}