const apiBase = 'http://localhost:8000';

export const api = {
  syncPosts(items){ return axios.post(`${apiBase}/api/posts/bulk`, { items }); },
  syncBrowse(items){ return axios.post(`${apiBase}/api/browse-log`, { items }); },
  listPosts(params){ return axios.get(`${apiBase}/api/posts`, { params }); },
  listBrowse(params){ return axios.get(`${apiBase}/api/browse-log`, { params }); },
  compareUrls(urls){ return axios.post(`${apiBase}/api/compare/urls`, { urls }); },
  trashBatch(payload){ return axios.post(`${apiBase}/api/trash/batch`, payload); },
  pushTg(url){ return axios.post(`${apiBase}/api/push/tg`, { url }); },

  buildTopic(payload){ return axios.post(`${apiBase}/api/topics/build`, payload); },
  listTopics(){ return axios.get(`${apiBase}/api/topics`); },
  getTopic(id){ return axios.get(`${apiBase}/api/topics/${id}`); },
  analyzeTopic(topicId, focus){ return axios.post(`${apiBase}/api/topics/${topicId}/analyze`, { focus }); },
  listEntities(){ return axios.get(`${apiBase}/api/entities`); },

  youtubeImport(urls, channel_name){ return axios.post(`${apiBase}/api/youtube/import`, { urls, channel_name }); },
  youtubeList(params){ return axios.get(`${apiBase}/api/youtube/items`, { params }); },
  youtubeAnalyze(item_ids){ return axios.post(`${apiBase}/api/youtube/analyze`, { item_ids }); },

  cryptoPull(payload){ return axios.post(`${apiBase}/api/crypto/pull`, payload); },
  cryptoBackfill(payload){ return axios.post(`${apiBase}/api/crypto/backfill`, payload); },
  cryptoList(params){ return axios.get(`${apiBase}/api/crypto/metrics`, { params }); },

  chartCapture(payload){ return axios.post(`${apiBase}/api/charts/capture`, payload); },
  chartAnalyze(item_id){ return axios.post(`${apiBase}/api/charts/analyze`, { item_id }); },
  chartList(params){ return axios.get(`${apiBase}/api/charts/snapshots`, { params }); },

  runBackup(target_dir){ return axios.post(`${apiBase}/api/backup/run`, { target_dir }); }
}
