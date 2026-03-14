// Last Edited: 2026-03-13
const normalizeBaseUrl = (value) => String(value || '').trim().replace(/\/+$/, '');

const deriveApiBase = () => {
  const configured = normalizeBaseUrl(window.__TRACE_API_BASE__ || window.TRACE_API_BASE);
  if (configured) return configured;

  const { hostname, port, origin } = window.location;
  const isLocalHost = ['localhost', '127.0.0.1'].includes(hostname);

  if (isLocalHost) {
    return normalizeBaseUrl(`http://${hostname}:8000`);
  }

  if (port === '8000') {
    return normalizeBaseUrl(origin);
  }

  return '';
};

const apiBase = deriveApiBase();

const buildUrl = (path) => `${apiBase}${path}`;

axios.defaults.withCredentials = true;

export const api = {
  authLogin(payload){ return axios.post(buildUrl('/api/auth/login'), payload); },
  authStatus(){ return axios.get(buildUrl('/api/auth/status')); },
  authLogout(){ return axios.post(buildUrl('/api/auth/logout')); },

  syncPosts(items){ return axios.post(buildUrl('/api/posts/bulk'), { items }); },
  syncBrowse(items){ return axios.post(buildUrl('/api/browse-log'), { items }); },
  listPosts(params){ return axios.get(buildUrl('/api/posts'), { params }); },
  listBrowse(params){ return axios.get(buildUrl('/api/browse-log'), { params }); },
  compareUrls(urls){ return axios.post(buildUrl('/api/compare/urls'), { urls }); },
  collectX(payload){ return axios.post(buildUrl('/api/collect'), payload); },
  trashBatch(payload){ return axios.post(buildUrl('/api/trash/batch'), payload); },
  pushTg(url){ return axios.post(buildUrl('/api/push/tg'), { url }); },
  xSyncItemToNotion(payload){ return axios.post(buildUrl('/api/x/notion-sync'), payload); },
  listXSourceFiles(){ return axios.get(buildUrl('/api/x/source/files')); },
  uploadXJsonFiles(formData){ return axios.post(buildUrl('/api/x/source/json-upload'), formData, { headers: { 'Content-Type': 'multipart/form-data' } }); },
  uploadXImageFolder(formData){ return axios.post(buildUrl('/api/x/source/image-folder-upload'), formData, { headers: { 'Content-Type': 'multipart/form-data' } }); },

  buildTopic(payload){ return axios.post(buildUrl('/api/topics/build'), payload); },
  listTopics(){ return axios.get(buildUrl('/api/topics')); },
  getTopic(id){ return axios.get(buildUrl(`/api/topics/${id}`)); },
  analyzeTopic(topicId, focus){ return axios.post(buildUrl(`/api/topics/${topicId}/analyze`), { focus }); },
  listEntities(){ return axios.get(buildUrl('/api/entities')); },

  youtubeImport(urls, channel_name){ return axios.post(buildUrl('/api/youtube/import'), { urls, channel_name }); },
  youtubeList(params){ return axios.get(buildUrl('/api/youtube/items'), { params }); },
  youtubeTask(task_id){ return axios.get(buildUrl(`/api/youtube/tasks/${task_id}`)); },
  youtubeAnalyze(item_ids){ return axios.post(buildUrl('/api/youtube/analyze'), { item_ids }); },
  youtubeSaveTranscript(item_id, content){ return axios.post(buildUrl(`/api/youtube/${item_id}/transcript`), { content }); },
  youtubeSyncToNotion(item_ids){ return axios.post(buildUrl('/api/youtube/notion/sync'), { item_ids }); },
  youtubeSyncItemToNotion(item_id){ return axios.post(buildUrl(`/api/youtube/${item_id}/notion-sync`)); },

  cryptoPull(payload){ return axios.post(buildUrl('/api/crypto/pull'), payload); },
  cryptoBackfill(payload){ return axios.post(buildUrl('/api/crypto/backfill'), payload); },
  cryptoList(params){ return axios.get(buildUrl('/api/crypto/metrics'), { params }); },

  chartCapture(payload){ return axios.post(buildUrl('/api/charts/capture'), payload); },
  chartManualUpload(formData){ return axios.post(buildUrl('/api/charts/manual-upload'), formData, { headers: { 'Content-Type': 'multipart/form-data' } }); },
  chartCaptureBatch(payload){ return axios.post(buildUrl('/api/charts/capture/batch'), payload); },
  chartAnalyze(item_id){ return axios.post(buildUrl('/api/charts/analyze'), { item_id }); },
  chartList(params){ return axios.get(buildUrl('/api/charts/snapshots'), { params }); },
  chartPushTg(payload){ return axios.post(buildUrl('/api/charts/push/tg'), payload); },

  youtubeDelete(item_ids){ return axios.post(buildUrl('/api/youtube/delete'), { item_ids }); },
  runBackup(target_dir){ return axios.post(buildUrl('/api/backup/run'), { target_dir }); },
  clearDatabase(target_dir){ return axios.post(buildUrl('/api/database/clear'), { target_dir }); }
}
