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
  },
  compareUrls(urls){
    return axios.post(`${apiBase}/api/compare/urls`, { urls });
  },
  buildTopic(payload){
    return axios.post(`${apiBase}/api/topics/build`, payload);
  },
  listTopics(){
    return axios.get(`${apiBase}/api/topics`);
  },
  analyzeTopic(topicId, focus){
    return axios.post(`${apiBase}/api/topics/${topicId}/analyze`, { focus });
  },
  youtubeImport(urls, channel_name){
    return axios.post(`${apiBase}/api/youtube/import`, { urls, channel_name });
  },
  cryptoPull(payload){
    return axios.post(`${apiBase}/api/crypto/pull`, payload);
  },
  chartCapture(payload){
    return axios.post(`${apiBase}/api/charts/capture`, payload);
  },
  runBackup(target_dir){
    return axios.post(`${apiBase}/api/backup/run`, { target_dir });
  }
}
