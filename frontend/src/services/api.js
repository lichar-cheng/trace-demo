// Last Edited: 2026-03-12
const apiBase = 'http://localhost:8000';

axios.defaults.withCredentials = true;

export const api = {
  authLogin(payload){ return axios.post(`${apiBase}/api/auth/login`, payload); },
  authStatus(){ return axios.get(`${apiBase}/api/auth/status`); },
  authLogout(){ return axios.post(`${apiBase}/api/auth/logout`); },

  syncPosts(items){ return axios.post(`${apiBase}/api/posts/bulk`, { items }); },
  syncBrowse(items){ return axios.post(`${apiBase}/api/browse-log`, { items }); },
  listPosts(params){ return axios.get(`${apiBase}/api/posts`, { params }); },
  listBrowse(params){ return axios.get(`${apiBase}/api/browse-log`, { params }); },
  compareUrls(urls){ return axios.post(`${apiBase}/api/compare/urls`, { urls }); },
  collectX(payload){ return axios.post(`${apiBase}/api/collect`, payload); },
  trashBatch(payload){ return axios.post(`${apiBase}/api/trash/batch`, payload); },
  pushTg(url){ return axios.post(`${apiBase}/api/push/tg`, { url }); },
  listXSourceFiles(){ return axios.get(`${apiBase}/api/x/source/files`); },
  uploadXJsonFiles(formData){ return axios.post(`${apiBase}/api/x/source/json-upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } }); },
  uploadXImageFolder(formData){ return axios.post(`${apiBase}/api/x/source/image-folder-upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } }); },

  buildTopic(payload){ return axios.post(`${apiBase}/api/topics/build`, payload); },
  listTopics(){ return axios.get(`${apiBase}/api/topics`); },
  getTopic(id){ return axios.get(`${apiBase}/api/topics/${id}`); },
  analyzeTopic(topicId, focus){ return axios.post(`${apiBase}/api/topics/${topicId}/analyze`, { focus }); },
  listEntities(){ return axios.get(`${apiBase}/api/entities`); },

  youtubeImport(urls, channel_name){ return axios.post(`${apiBase}/api/youtube/import`, { urls, channel_name }); },
  youtubeList(params){ return axios.get(`${apiBase}/api/youtube/items`, { params }); },
  youtubeTask(task_id){ return axios.get(`${apiBase}/api/youtube/tasks/${task_id}`); },
  youtubeAnalyze(item_ids){ return axios.post(`${apiBase}/api/youtube/analyze`, { item_ids }); },

  cryptoPull(payload){ return axios.post(`${apiBase}/api/crypto/pull`, payload); },
  cryptoBackfill(payload){ return axios.post(`${apiBase}/api/crypto/backfill`, payload); },
  cryptoList(params){ return axios.get(`${apiBase}/api/crypto/metrics`, { params }); },

  chartCapture(payload){ return axios.post(`${apiBase}/api/charts/capture`, payload); },
  chartAnalyze(item_id){ return axios.post(`${apiBase}/api/charts/analyze`, { item_id }); },
  chartList(params){ return axios.get(`${apiBase}/api/charts/snapshots`, { params }); },

  youtubeDelete(item_ids){ return axios.post(`${apiBase}/api/youtube/delete`, { item_ids }); },
  runBackup(target_dir){ return axios.post(`${apiBase}/api/backup/run`, { target_dir }); }
}
