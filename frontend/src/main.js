const { createApp, reactive, computed, onMounted } = Vue;
import { api } from './services/api.js';

const API_BASE = 'http://152.32.174.6:8000';

createApp({
  setup() {
    const state = reactive({
      view: 'x',
      status: '',
      loading: false,
      auth: {
        ready: false,
        loggedIn: false,
        username: '',
        password: '',
      },
      x: {
        posts: [],
        activeIndex: 0,
        keyword: '',
        compareInput: '',
        toolsOpen: false,
        importSummary: '',
        localPosts: [],
        localDirectoryOptions: [],
        selectedDirectories: [],
        mobilePane: 'list',
        detailOpen: false,
        localMediaMap: {},
      },
      youtube: {
        urlInput: '',
        items: [],
        authorFilter: '',
        startTime: '',
        endTime: '',
        statusFilter: '',
        activeId: null,
        mobilePane: 'list',
        detailOpen: false,
        editMode: false,
        editDraft: '',
      },
      crypto: {
        symbol: 'BTCUSDT',
        metric_name: 'open_interest',
        market_type: 'future',
        interval: '1h',
        value: 0,
        items: [],
      },
      charts: {
        page_url: 'https://www.tradingview.com',
        platform: 'tradingview',
        symbol: 'BTCUSDT',
        timeframe: '4h',
        image_path: '',
        items: [],
      },
      topic: {
        topic_name: '',
        topic_type: 'event',
        description: '',
        focus: 'global market',
        topics: [],
        entities: [],
      },
    });

    const setStatus = (msg) => {
      state.status = `[${new Date().toLocaleTimeString()}] ${msg}`;
    };

    const safeRun = async (fn) => {
      state.loading = true;
      try {
        await fn();
      } catch (error) {
        if (error?.response?.status === 401) {
          state.auth.loggedIn = false;
          state.auth.ready = true;
        }
        const responseData = error?.response?.data || {};
        const detail = responseData.detail || responseData.results?.[0]?.reason || responseData.error || error.message;
        setStatus(`Failed: ${detail}`);
      } finally {
        state.loading = false;
      }
    };

    const formatDateTime = (value) => {
      if (!value) return '';
      const dt = new Date(value);
      if (Number.isNaN(dt.getTime())) return value;
      return dt.toLocaleString();
    };

    const resolveMediaUrl = (value) => {
      if (!value) return '';
      return value.startsWith('http') ? value : `${API_BASE}${value}`;
    };

    const xSourcePosts = computed(() => {
      if (state.x.localPosts.length) {
        const selected = new Set(state.x.selectedDirectories);
        return state.x.localPosts.filter((post) => selected.has(post.sourceDirectory));
      }
      return state.x.posts;
    });

    const xDirectoryGroups = computed(() => {
      const groups = { x: [], uploads: [] };
      state.x.localDirectoryOptions.forEach((item) => {
        const bucket = item.bucket === 'uploads' ? 'uploads' : 'x';
        groups[bucket].push(item);
      });
      return groups;
    });

    const xFiltered = computed(() => {
      const key = state.x.keyword.trim().toLowerCase();
      return xSourcePosts.value.filter((post) => {
        if (!key) return true;
        return [post.text, post.kol_name, post.kol_handle, post.url, post.posted_at, post.sourceDirectory]
          .some((field) => (field || '').toLowerCase().includes(key));
      });
    });

    const xActive = computed(() => xFiltered.value[state.x.activeIndex] || null);

    const youtubeFiltered = computed(() => state.youtube.items);
    const youtubeActive = computed(() => (
      state.youtube.items.find((item) => item.id === state.youtube.activeId) || youtubeFiltered.value[0] || null
    ));

    const normalizePath = (value) => String(value || '').replace(/\\/g, '/').replace(/^\.?\//, '');
    const fileNameFromPath = (value) => normalizePath(value).split('/').filter(Boolean).pop() || '';
    const prettifyStem = (value) => String(value || '')
      .replace(/\.[^/.]+$/, '')
      .replace(/[_-]([A-Za-z0-9_-]{11})$/, '')
      .replace(/[_-]+/g, ' ')
      .trim();

    const displayYoutubeTitle = (item) => {
      if (!item) return '';
      const rawTitle = (item.extra?.display_title || item.extra?.video_title || item.title || '').trim();
      if (rawTitle && !/^YouTube:\s*https?:\/\//i.test(rawTitle)) {
        return rawTitle;
      }
      const url = item.url || '';
      try {
        const parsed = new URL(url);
        const id = parsed.searchParams.get('v') || parsed.pathname.split('/').filter(Boolean).pop() || 'video';
        return `YouTube Video ${id}`;
      } catch {
        return rawTitle || url || 'YouTube Video';
      }
    };

    const displayYoutubeAuthor = (item) => {
      return item?.author_name || item?.extra?.uploader || item?.extra?.channel_name || 'Unknown author';
    };

    const displayYoutubeTime = (item) => {
      return formatDateTime(item?.publish_time || item?.extra?.publish_time || item?.extra?.upload_date || '');
    };

    const isNotionSynced = (item) => !!(item?.notion_synced_at || item?.extra?.notion_synced_at);

    const normalizeImportedPost = (item, fallbackIndex = 0) => {
      const text = item.text || item.full_text || item.content_raw || item.content_cleaned || item.summary || '';
      const images = item.image_urls || item.media_urls || item.media_paths || [];
      const normalizedImages = Array.isArray(images)
        ? images.filter(Boolean)
        : String(images || '').split(',').map((part) => part.trim()).filter(Boolean);
      const handle = item.kol_handle || item.user_handle || item.author_name || item.handle || `imported_${fallbackIndex}`;
      const idPart = item.id || `${Date.now()}_${fallbackIndex}`;
      return {
        kol_handle: handle,
        kol_name: item.kol_name || item.name || item.author_name || handle,
        kol_avatar_url: item.kol_avatar_url || '',
        posted_at: item.posted_at || item.created_at || item.publish_time || null,
        text,
        image_urls: normalizedImages,
        likes: Number(item.likes ?? item.extra?.likes ?? 0),
        retweets: Number(item.retweets ?? item.extra?.retweets ?? 0),
        replies: Number(item.replies ?? item.extra?.replies ?? 0),
        url: item.url || `https://x.com/${handle}/status/${idPart}`,
        sourceDirectory: item.sourceDirectory || 'database',
        sourceDirectoryLabel: item.sourceDirectoryLabel || item.sourceDirectory || 'database',
      };
    };

    const resolveLocalMediaRefs = (images, sourceDirectory, mediaMap) => {
      const values = Array.isArray(images)
        ? images
        : String(images || '').split(',').map((part) => part.trim()).filter(Boolean);
      return values.map((value) => {
        if (!value) return '';
        if (value.startsWith('http')) return value;
        const normalized = normalizePath(value);
        const candidates = [normalized, normalizePath(`${sourceDirectory}/${normalized}`), fileNameFromPath(normalized)];
        const match = candidates.find((candidate) => mediaMap[candidate]);
        return match ? mediaMap[match] : value;
      }).filter(Boolean);
    };

    const applySourcePayload = (data) => {
      const posts = (data.items || []).map((item, index) => normalizeImportedPost(item, index));
      state.x.localPosts = posts;
      state.x.localDirectoryOptions = (data.directories || []).map((item) => ({
        name: item.name,
        count: item.count,
        bucket: item.bucket || 'x',
      }));
      state.x.selectedDirectories = state.x.localDirectoryOptions.map((item) => item.name);
      state.x.activeIndex = 0;
      state.x.detailOpen = false;
    };

    const loadXSourceFiles = async (message = '') => {
      const { data } = await api.listXSourceFiles();
      applySourcePayload(data);
      if (message) {
        state.x.importSummary = `${message} Loaded ${state.x.localPosts.length} posts from source files`;
        setStatus(state.x.importSummary);
      }
    };

    const handleImportFile = async (event) => {
      const files = Array.from(event.target.files || []);
      event.target.value = '';
      if (!files.length) return;
      await safeRun(async () => {
        const formData = new FormData();
        files.forEach((file) => formData.append('files', file, file.name));
        const { data } = await api.uploadXJsonFiles(formData);
        await loadXSourceFiles(`Uploaded ${data.saved_files?.length || files.length} JSON file(s) to uploads.`);
      });
    };

    const handleImportFolder = async (event) => {
      const files = Array.from(event.target.files || []);
      event.target.value = '';
      if (!files.length) {
        setStatus('No files found in selected folder');
        return;
      }
      await safeRun(async () => {
        const formData = new FormData();
        files.forEach((file) => {
          formData.append('files', file, file.name);
          formData.append('relative_paths', file.webkitRelativePath || file.name);
        });
        const { data } = await api.uploadXImageFolder(formData);
        state.x.localMediaMap = data.image_map || {};
        state.x.localPosts = state.x.localPosts.map((post) => ({
          ...post,
          image_urls: resolveLocalMediaRefs(post.image_urls, post.sourceDirectory, state.x.localMediaMap),
        }));
        state.x.importSummary = `Uploaded ${data.saved_images || 0} image file(s) to images/${data.folder_name || ''}`;
        setStatus(state.x.importSummary);
      });
    };

    const toggleDirectory = (directory) => {
      const set = new Set(state.x.selectedDirectories);
      if (set.has(directory)) {
        set.delete(directory);
      } else {
        set.add(directory);
      }
      state.x.selectedDirectories = state.x.localDirectoryOptions
        .map((item) => item.name)
        .filter((name) => set.has(name));
      state.x.activeIndex = 0;
    };

    const selectAllDirectories = () => {
      state.x.selectedDirectories = state.x.localDirectoryOptions.map((item) => item.name);
      state.x.activeIndex = 0;
    };

    const clearLocalSource = () => {
      state.x.localPosts = [];
      state.x.localDirectoryOptions = [];
      state.x.selectedDirectories = [];
      state.x.localMediaMap = {};
      state.x.activeIndex = 0;
      state.x.detailOpen = false;
      setStatus('Cleared source-file view');
    };

    const selectXPost = (index) => {
      state.x.activeIndex = index;
      state.x.detailOpen = true;
      if (window.innerWidth <= 900) {
        state.x.mobilePane = 'detail';
      }
    };

    const showXList = () => {
      state.x.mobilePane = 'list';
    };

    const showXDetail = () => {
      state.x.detailOpen = true;
      state.x.mobilePane = 'detail';
    };

    const closeXDetail = () => {
      state.x.detailOpen = false;
      state.x.mobilePane = 'list';
    };

    const loadX = async () => safeRun(async () => {
      const { data } = await api.listPosts({ limit: 300 });
      state.x.posts = data;
      await loadXSourceFiles();
      state.x.activeIndex = 0;
      state.x.mobilePane = 'list';
      state.x.detailOpen = false;
      setStatus(`Loaded ${data.length} X posts`);
    });

    const xCompare = async () => safeRun(async () => {
      const urls = state.x.compareInput.split('\n').map((line) => line.trim()).filter(Boolean);
      if (!urls.length) {
        setStatus('Paste one or more URLs to compare');
        return;
      }
      const { data } = await api.compareUrls(urls);
      setStatus(`Compare done: exists ${data.exists.length}, missing ${data.missing.length}`);
    });

    const xDelete = async () => {
      if (!xActive.value) return;
      await safeRun(async () => {
        await api.trashBatch({ urls: [xActive.value.url] });
        await loadX();
        setStatus('Post deleted');
      });
    };

    const xPushTg = async () => {
      if (!xActive.value) return;
      if (!xActive.value.id && !xActive.value.url) {
        setStatus('This X post is missing both id and url');
        return;
      }
      await safeRun(async () => {
        const activeId = xActive.value.id;
        const activeUrl = xActive.value.url || '';
        const { data } = await api.xSyncItemToNotion({
          post_id: activeId || null,
          url: activeUrl,
        });
        await loadX();
        const idx = xFiltered.value.findIndex((item) => (
          (activeId && item.id === activeId) || (!activeId && item.url === activeUrl)
        ));
        state.x.activeIndex = idx >= 0 ? idx : state.x.activeIndex;
        state.x.detailOpen = true;
        const result = data.results?.[0];
        if (result?.status === 'failed') {
          setStatus(`Notion sync failed: ${result.reason || data.detail || data.error || 'unknown error'}`);
          return;
        }
        setStatus(`Notion sync ${result?.status || 'done'} for post ${activeId || activeUrl}`);
      });
    };

    const xExport = () => {
      const blob = new Blob([JSON.stringify(xFiltered.value, null, 2)], { type: 'application/json' });
      const anchor = document.createElement('a');
      anchor.href = URL.createObjectURL(blob);
      anchor.download = `x-library-${Date.now()}.json`;
      anchor.click();
      URL.revokeObjectURL(anchor.href);
      setStatus('Export completed');
    };

    const loadYoutube = async () => safeRun(async () => {
      const params = { limit: 100 };
      if (state.youtube.authorFilter.trim()) params.author_name = state.youtube.authorFilter.trim();
      if (state.youtube.startTime) params.start_time = new Date(state.youtube.startTime).toISOString();
      if (state.youtube.endTime) params.end_time = new Date(state.youtube.endTime).toISOString();
      if (state.youtube.statusFilter) params.analysis_status = state.youtube.statusFilter;
      const { data } = await api.youtubeList(params);
      state.youtube.items = data;
      state.youtube.activeId = data[0]?.id || null;
      state.youtube.mobilePane = 'list';
      state.youtube.detailOpen = false;
      state.youtube.editMode = false;
      state.youtube.editDraft = '';
      setStatus(`Loaded ${data.length} YouTube items`);
    });

    const importYoutube = async () => safeRun(async () => {
      const urls = state.youtube.urlInput.split('\n').map((line) => line.trim()).filter(Boolean);
      if (!urls.length) {
        setStatus('Enter one or more YouTube URLs');
        return;
      }
      const { data } = await api.youtubeImport(urls, null);
      await loadYoutube();
      if (!data.created && data.requested) {
        setStatus(`Imported 0/${data.requested}. These URLs are probably already in the library.`);
        return;
      }
      state.youtube.urlInput = '';
      setStatus(`Imported ${data.created}/${data.requested} YouTube items`);
    });

    const analyzeYoutube = async (item) => safeRun(async () => {
      const { data } = await api.youtubeAnalyze([item.id]);
      await loadYoutube();
      setStatus(`Analyzed ${data.analyzed} YouTube item`);
    });

    const openYoutubeEditor = () => {
      if (!youtubeActive.value) return;
      state.youtube.editMode = true;
      state.youtube.editDraft = youtubeActive.value.content_raw || youtubeActive.value.content_cleaned || '';
    };

    const cancelYoutubeEditor = () => {
      state.youtube.editMode = false;
      state.youtube.editDraft = '';
    };

    const saveYoutubeTranscript = async () => {
      if (!youtubeActive.value) return;
      const activeId = youtubeActive.value.id;
      await safeRun(async () => {
        await api.youtubeSaveTranscript(activeId, state.youtube.editDraft);
        state.youtube.editMode = false;
        await loadYoutube();
        state.youtube.activeId = activeId;
        state.youtube.detailOpen = true;
        if (window.innerWidth <= 900) {
          state.youtube.mobilePane = 'detail';
        }
        setStatus('Transcript saved to file');
      });
    };

    const syncYoutubeToNotion = async () => {
      if (!youtubeActive.value) return;
      const activeId = youtubeActive.value.id;
      await safeRun(async () => {
        const { data } = await api.youtubeSyncItemToNotion(activeId);
        await loadYoutube();
        state.youtube.activeId = activeId;
        state.youtube.detailOpen = true;
        if (window.innerWidth <= 900) {
          state.youtube.mobilePane = 'detail';
        }
        const result = data.results?.[0];
        if (result?.status === 'failed') {
          setStatus(`Notion sync failed: ${result.reason || data.detail || 'unknown error'}`);
          return;
        }
        setStatus(`Notion sync ${result?.status || 'done'} for item ${activeId}`);
      });
    };

    const selectYoutubeItem = (itemId) => {
      state.youtube.activeId = itemId;
      state.youtube.detailOpen = true;
      state.youtube.editMode = false;
      state.youtube.editDraft = '';
      if (window.innerWidth <= 900) {
        state.youtube.mobilePane = 'detail';
      }
    };

    const showYoutubeList = () => {
      state.youtube.mobilePane = 'list';
    };

    const showYoutubeDetail = () => {
      if (youtubeActive.value) {
        state.youtube.detailOpen = true;
        state.youtube.mobilePane = 'detail';
      }
    };

    const closeYoutubeDetail = () => {
      state.youtube.detailOpen = false;
      state.youtube.mobilePane = 'list';
      state.youtube.editMode = false;
      state.youtube.editDraft = '';
    };

    const loadCrypto = async () => safeRun(async () => {
      const { data } = await api.cryptoList({ limit: 100 });
      state.crypto.items = data;
      setStatus(`Loaded ${data.length} crypto metrics`);
    });

    const pullCrypto = async () => safeRun(async () => {
      await api.cryptoPull({
        metric_name: state.crypto.metric_name,
        symbol: state.crypto.symbol,
        market_type: state.crypto.market_type,
        interval: state.crypto.interval,
        value: Number(state.crypto.value || 0),
      });
      await loadCrypto();
      setStatus('Crypto metric inserted');
    });

    const backfillCrypto = async () => safeRun(async () => {
      const now = new Date();
      const start = new Date(now.getTime() - 3600_000 * 12);
      await api.cryptoBackfill({
        metric_name: state.crypto.metric_name,
        symbol: state.crypto.symbol,
        market_type: state.crypto.market_type,
        interval: state.crypto.interval,
        start_time: start.toISOString(),
        end_time: now.toISOString(),
        values: [101, 117, 112, 126, 135, 129],
      });
      await loadCrypto();
      setStatus('Crypto history backfilled');
    });

    const loadCharts = async () => safeRun(async () => {
      const { data } = await api.chartList({ limit: 100 });
      state.charts.items = data;
      setStatus(`Loaded ${data.length} chart snapshots`);
    });

    const captureChart = async () => safeRun(async () => {
      await api.chartCapture({
        page_url: state.charts.page_url,
        platform: state.charts.platform,
        symbol: state.charts.symbol,
        timeframe: state.charts.timeframe,
        image_path: state.charts.image_path || `data/charts/snapshots/${Date.now()}.png`,
      });
      await loadCharts();
      setStatus('Chart snapshot captured');
    });

    const analyzeChart = async (item) => safeRun(async () => {
      await api.chartAnalyze(item.id);
      await loadCharts();
      setStatus(`Chart #${item.id} analyzed`);
    });

    const loadTopic = async () => safeRun(async () => {
      const [{ data: topics }, { data: entities }] = await Promise.all([
        api.listTopics(),
        api.listEntities(),
      ]);
      state.topic.topics = topics;
      state.topic.entities = entities;
      setStatus(`Loaded ${topics.length} topics and ${entities.length} entities`);
    });

    const createTopic = async () => safeRun(async () => {
      if (!state.topic.topic_name.trim()) {
        setStatus('Enter a topic name');
        return;
      }
      await api.buildTopic({
        topic_name: state.topic.topic_name,
        topic_type: state.topic.topic_type,
        description: state.topic.description,
        item_ids: [],
      });
      state.topic.topic_name = '';
      state.topic.description = '';
      await loadTopic();
      setStatus('Topic created');
    });

    const analyzeTopic = async (item) => safeRun(async () => {
      await api.analyzeTopic(item.id, state.topic.focus);
      await loadTopic();
      setStatus(`Topic #${item.id} analyzed`);
    });

    const backup = async () => safeRun(async () => {
      const { data } = await api.runBackup('data/backup');
      setStatus(`Backup created: ${data.backup}`);
    });

    const clearDatabase = async () => {
      const confirmed = window.confirm('This will back up the database and then clear all rows. Continue?');
      if (!confirmed) return;
      await safeRun(async () => {
        const { data } = await api.clearDatabase('data/backup');
        state.x.posts = [];
        state.youtube.items = [];
        state.crypto.items = [];
        state.charts.items = [];
        state.topic.topics = [];
        state.topic.entities = [];
        setStatus(`Database cleared after backup: ${data.backup}`);
      });
    };

    const loadCurrentView = async () => {
      if (state.view === 'x') await loadX();
      if (state.view === 'youtube') await loadYoutube();
      if (state.view === 'crypto') await loadCrypto();
      if (state.view === 'charts') await loadCharts();
      if (state.view === 'topic') await loadTopic();
    };

    const checkAuth = async () => {
      try {
        const { data } = await api.authStatus();
        state.auth.loggedIn = !!data.authenticated;
        state.auth.ready = true;
        if (data.authenticated) {
          state.auth.username = data.username || '';
        }
      } catch {
        state.auth.loggedIn = false;
        state.auth.ready = true;
      }
    };

    const login = async () => safeRun(async () => {
      if (!state.auth.username.trim() || !state.auth.password.trim()) {
        setStatus('Enter username and password');
        return;
      }
      await api.authLogin({
        username: state.auth.username.trim(),
        password: state.auth.password,
      });
      state.auth.loggedIn = true;
      state.auth.ready = true;
      state.auth.password = '';
      await loadCurrentView();
      setStatus('Login successful');
    });

    const logout = async () => safeRun(async () => {
      await api.authLogout();
      state.auth.loggedIn = false;
      state.auth.ready = true;
      state.x.detailOpen = false;
      state.youtube.detailOpen = false;
      setStatus('Logged out');
    });

    const switchView = async (view) => {
      state.view = view;
      if (!state.auth.loggedIn) return;
      await loadCurrentView();
    };

    onMounted(async () => {
      await checkAuth();
      if (state.auth.loggedIn) {
        await loadX();
        await loadYoutube();
        await loadCrypto();
        await loadCharts();
        await loadTopic();
      }
    });

    return {
      state,
      xFiltered,
      xActive,
      xDirectoryGroups,
      youtubeFiltered,
      youtubeActive,
      displayYoutubeTitle,
      displayYoutubeAuthor,
      displayYoutubeTime,
      isNotionSynced,
      formatDateTime,
      resolveMediaUrl,
      switchView,
      loadYoutube,
      xCompare,
      xDelete,
      xPushTg,
      xExport,
      handleImportFile,
      handleImportFolder,
      toggleDirectory,
      selectAllDirectories,
      clearLocalSource,
      selectXPost,
      showXList,
      showXDetail,
      closeXDetail,
      importYoutube,
      analyzeYoutube,
      openYoutubeEditor,
      cancelYoutubeEditor,
      saveYoutubeTranscript,
      syncYoutubeToNotion,
      selectYoutubeItem,
      showYoutubeList,
      showYoutubeDetail,
      closeYoutubeDetail,
      pullCrypto,
      backfillCrypto,
      captureChart,
      analyzeChart,
      createTopic,
      analyzeTopic,
      backup,
      clearDatabase,
      login,
      logout,
    };
  },
  template: `
    <div v-if="!state.auth.ready" class="auth-shell">
      <div class="auth-card card">
        <h1>Checking Access</h1>
        <div class="muted">Waiting for backend authentication status...</div>
      </div>
    </div>

    <div v-else-if="!state.auth.loggedIn" class="auth-shell">
      <div class="auth-card card">
        <h1>Sign In</h1>
        <div class="muted">Use the fixed account and password configured for this deployment.</div>
        <input v-model="state.auth.username" placeholder="Username" @keyup.enter="login" />
        <input v-model="state.auth.password" type="password" placeholder="Password" @keyup.enter="login" />
        <button class="action primary full" @click="login">Login</button>
        <div class="status auth-status">{{ state.status }}</div>
      </div>
    </div>

    <div v-else class="app-shell">
      <aside class="side">
        <div class="logo">Knowledge Base</div>
        <button class="nav" :class="{active: state.view === 'x'}" @click="switchView('x')">X Library</button>
        <button class="nav" :class="{active: state.view === 'youtube'}" @click="switchView('youtube')">YTube Library</button>
        <button class="nav" :class="{active: state.view === 'crypto'}" @click="switchView('crypto')">CT Metrics</button>
        <button class="nav" :class="{active: state.view === 'charts'}" @click="switchView('charts')">Chart Snapshots</button>
        <button class="nav" :class="{active: state.view === 'topic'}" @click="switchView('topic')">Topic Intelligence</button>
        <div class="side-bottom">
          <button class="action full" @click="backup">Backup</button>
          <button class="action full danger" @click="clearDatabase">Clear DB</button>
          <button class="action full" @click="logout">Logout</button>
        </div>
      </aside>

      <main class="main">
        <header class="header">
          <h1 v-if="state.view === 'x'">X Library</h1>
          <h1 v-else-if="state.view === 'youtube'">YTube Library</h1>
          <h1 v-else-if="state.view === 'crypto'">CT Metrics</h1>
          <h1 v-else-if="state.view === 'charts'">Analysis & Snapshots</h1>
          <h1 v-else>Topic Intelligence</h1>
          <span class="status" :class="{loading: state.loading}">{{ state.loading ? 'Loading...' : state.status }}</span>
        </header>

        <section v-if="state.view === 'x'" class="pane x-layout">
          <div class="toolbar">
            <input v-model="state.x.keyword" placeholder="Search posts, users, URLs..." />
            <button class="action" @click="state.x.toolsOpen = !state.x.toolsOpen">{{ state.x.toolsOpen ? 'Hide tools' : 'Tools' }}</button>
          </div>

          <div v-if="state.x.toolsOpen" class="card tool-panel">
            <div class="tool-header">Data source</div>
            <div class="tool-subgrid">
              <label class="file-action">
                <span class="action">Upload JSON To uploads</span>
                <input type="file" accept=".json,application/json" multiple @change="handleImportFile" />
              </label>
              <label class="file-action">
                <span class="action">Upload Image Folder</span>
                <input type="file" webkitdirectory directory multiple @change="handleImportFolder" />
              </label>
              <button class="action" @click="clearLocalSource">Clear Local Source</button>
              <button class="action" @click="xExport">Export Current View</button>
            </div>
            <div v-if="state.x.importSummary" class="muted">{{ state.x.importSummary }}</div>
            <div v-if="state.x.localDirectoryOptions.length" class="directory-panel">
              <div class="row-top">
                <div class="tool-header">Directories</div>
                <button class="action" @click="selectAllDirectories">Select All</button>
              </div>
              <div class="directory-buckets">
                <div v-if="xDirectoryGroups.x.length" class="directory-block">
                  <div class="muted">x</div>
                  <div class="directory-grid">
                    <button
                      v-for="option in xDirectoryGroups.x"
                      :key="option.name"
                      class="directory-chip"
                      :class="{ active: state.x.selectedDirectories.includes(option.name) }"
                      @click="toggleDirectory(option.name)"
                    >
                      {{ option.label || option.name }} ({{ option.count }})
                    </button>
                  </div>
                </div>
                <div v-if="xDirectoryGroups.uploads.length" class="directory-block">
                  <div class="muted">uploads</div>
                  <div class="directory-grid">
                    <button
                      v-for="option in xDirectoryGroups.uploads"
                      :key="option.name"
                      class="directory-chip"
                      :class="{ active: state.x.selectedDirectories.includes(option.name) }"
                      @click="toggleDirectory(option.name)"
                    >
                      {{ option.label || option.name }} ({{ option.count }})
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <textarea v-model="state.x.compareInput" placeholder="Paste one URL per line to compare"></textarea>
            <div class="actions-row">
              <button class="action" @click="xCompare">Compare URLs</button>
            </div>
          </div>

          <div class="x-grid">
            <div class="mobile-pane-toggle">
              <button class="action" :class="{ primary: state.x.mobilePane === 'list' }" @click="showXList">List</button>
              <button class="action" :class="{ primary: state.x.mobilePane === 'detail' }" @click="showXDetail" :disabled="!xActive">Detail</button>
            </div>

            <div class="card list post-list" :class="{ 'mobile-hidden': state.x.mobilePane === 'detail' }">
              <div
                v-for="(post, idx) in xFiltered"
                :key="post.url || idx"
                class="item post-row"
                :class="{active: idx === state.x.activeIndex}"
                @click="selectXPost(idx)"
              >
                <div class="row-top">
                  <div class="title">{{ post.kol_name || post.kol_handle }}</div>
                  <div class="muted">{{ formatDateTime(post.posted_at || post.created_at) }}</div>
                </div>
                <div class="muted">@{{ post.kol_handle }}</div>
                <div class="muted" v-if="post.sourceDirectoryLabel && post.sourceDirectoryLabel !== 'database'">{{ post.sourceDirectoryLabel }}</div>
                <div class="text clamp-3">{{ post.text }}</div>
              </div>
            </div>

            <div class="card detail detail-hero" :class="{ 'mobile-hidden': state.x.mobilePane === 'list' }" v-if="xActive && state.x.detailOpen">
              <div class="detail-head">
                <div>
                  <h2>{{ xActive.kol_name || xActive.kol_handle }}</h2>
                  <div class="muted">@{{ xActive.kol_handle }}</div>
                  <div class="muted">{{ formatDateTime(xActive.posted_at || xActive.created_at) }}</div>
                </div>
                <a class="link" :href="xActive.url" target="_blank" rel="noreferrer">Open Original</a>
              </div>

              <div class="body-card">
                <div class="section-label">Post body</div>
                <p class="body-copy">{{ xActive.text }}</p>
              </div>

              <div v-if="xActive.image_urls && xActive.image_urls.length" class="body-card">
                <div class="section-label">Images</div>
                <div class="image-grid">
                  <img
                    v-for="(img, idx) in xActive.image_urls"
                    :key="img || idx"
                    :src="resolveMediaUrl(img)"
                    class="detail-image"
                  />
                </div>
              </div>

              <div class="actions-row">
                <span v-if="isNotionSynced(xActive)" class="badge">Notion Synced</span>
                <button class="action" @click="closeXDetail">Close Detail</button>
                <button class="action danger" @click="xDelete">Delete</button>
                <button class="action" :disabled="isNotionSynced(xActive) || (!xActive.id && !xActive.url)" @click="xPushTg">
                  {{ isNotionSynced(xActive) ? 'Synced To Notion' : 'Sync To Notion' }}
                </button>
              </div>
            </div>

            <div class="card detail empty-state" :class="{ 'mobile-hidden': state.x.mobilePane === 'list' }" v-else>Select a post from the left list.</div>
          </div>
        </section>

        <section v-else-if="state.view === 'youtube'" class="pane">
          <div class="toolbar">
            <input v-model="state.youtube.urlInput" placeholder="One YouTube URL per line" />
            <button class="action primary" @click="importYoutube">Import Metadata</button>
          </div>

          <div class="toolbar">
            <input v-model="state.youtube.authorFilter" placeholder="Filter by author" style="max-width: 220px" />
            <input v-model="state.youtube.startTime" type="datetime-local" style="max-width: 220px" />
            <input v-model="state.youtube.endTime" type="datetime-local" style="max-width: 220px" />
            <select v-model="state.youtube.statusFilter" style="max-width: 180px">
              <option value="">All status</option>
              <option value="pending">pending</option>
              <option value="processing">processing</option>
              <option value="done">done</option>
              <option value="failed">failed</option>
            </select>
            <button class="action" @click="loadYoutube">Filter</button>
          </div>

          <div class="youtube-layout">
            <div class="mobile-pane-toggle">
              <button class="action" :class="{ primary: state.youtube.mobilePane === 'list' }" @click="showYoutubeList">List</button>
              <button class="action" :class="{ primary: state.youtube.mobilePane === 'detail' }" @click="showYoutubeDetail" :disabled="!youtubeActive">Detail</button>
            </div>

            <div class="card list youtube-list" :class="{ 'mobile-hidden': state.youtube.mobilePane === 'detail' }">
              <div
                v-for="item in youtubeFiltered"
                :key="item.id"
                class="item post-row"
                :class="{ active: item.id === state.youtube.activeId }"
                @click="selectYoutubeItem(item.id)"
              >
                <div class="title">{{ displayYoutubeTitle(item) }}</div>
                <div class="muted">{{ displayYoutubeAuthor(item) }}</div>
                <div class="muted">{{ displayYoutubeTime(item) }}</div>
                <div class="badge-row">
                  <span class="badge">{{ item.analysis_status || 'pending' }}</span>
                  <span class="badge">{{ displayYoutubeTime(item) || 'Unknown time' }}</span>
                </div>
                <div class="text clamp-3">{{ item.content_raw || item.content_cleaned || item.analysis_result || 'No transcript yet.' }}</div>
              </div>
            </div>

            <div class="card detail detail-hero" :class="{ 'mobile-hidden': state.youtube.mobilePane === 'list' }" v-if="youtubeActive && state.youtube.detailOpen">
              <div class="detail-head">
                <div>
                  <h2>{{ displayYoutubeTitle(youtubeActive) }}</h2>
                  <div class="muted">{{ displayYoutubeAuthor(youtubeActive) }}</div>
                  <div class="muted">{{ displayYoutubeTime(youtubeActive) }}</div>
                </div>
                <a class="link" :href="youtubeActive.url" target="_blank" rel="noreferrer">Open Video</a>
              </div>

              <div class="badge-row">
                <span class="badge">{{ youtubeActive.analysis_status || 'pending' }}</span>
                <span class="badge">{{ displayYoutubeTime(youtubeActive) || 'Unknown time' }}</span>
                <span v-if="isNotionSynced(youtubeActive)" class="badge">Notion Synced</span>
              </div>

              <div class="body-card">
                <div class="section-label">Time</div>
                <div class="muted">{{ displayYoutubeTime(youtubeActive) || 'Unknown time' }}</div>
              </div>

              <div class="body-card">
                <div class="section-label">Transcript</div>
                <textarea
                  v-if="state.youtube.editMode"
                  v-model="state.youtube.editDraft"
                  class="editor-area"
                  placeholder="Paste the corrected transcript here"
                ></textarea>
                <p v-else class="body-copy subtitle-copy">{{ youtubeActive.content_raw || youtubeActive.content_cleaned || youtubeActive.analysis_result || 'No transcript content yet.' }}</p>
              </div>

              <div class="actions-row">
                <button class="action" @click="closeYoutubeDetail">Close Detail</button>
                <button v-if="!state.youtube.editMode" class="action" @click="openYoutubeEditor">Edit Transcript</button>
                <button v-if="state.youtube.editMode" class="action primary" @click="saveYoutubeTranscript">Save Transcript</button>
                <button v-if="state.youtube.editMode" class="action" @click="cancelYoutubeEditor">Cancel Edit</button>
                <button class="action" :disabled="isNotionSynced(youtubeActive)" @click="syncYoutubeToNotion">
                  {{ isNotionSynced(youtubeActive) ? 'Synced To Notion' : 'Sync This To Notion' }}
                </button>
                <button v-if="youtubeActive.analysis_status !== 'done'" class="action primary" @click="analyzeYoutube(youtubeActive)">Analyze</button>
              </div>
            </div>

            <div class="card detail empty-state" :class="{ 'mobile-hidden': state.youtube.mobilePane === 'list' }" v-else>Select a YouTube item from the list.</div>
          </div>
        </section>

        <section v-else-if="state.view === 'crypto'" class="pane">
          <div class="toolbar">
            <input v-model="state.crypto.symbol" placeholder="Symbol" style="max-width: 150px" />
            <input v-model="state.crypto.metric_name" placeholder="Metric" style="max-width: 180px" />
            <input v-model="state.crypto.interval" placeholder="Interval" style="max-width: 120px" />
            <input v-model="state.crypto.value" placeholder="Value" style="max-width: 140px" />
            <button class="action primary" @click="pullCrypto">Fetch Metrics</button>
            <button class="action" @click="backfillCrypto">Backfill</button>
          </div>

          <div class="card cards-grid">
            <div class="snapshot" v-for="item in state.crypto.items" :key="item.id">
              <div class="title">{{ item.title }}</div>
              <div class="muted">{{ item.extra.metric_name }} · {{ item.extra.interval }}</div>
              <div class="muted">{{ formatDateTime(item.publish_time) }}</div>
              <div class="value">{{ item.extra.value }}</div>
            </div>
          </div>
        </section>

        <section v-else-if="state.view === 'charts'" class="pane">
          <div class="toolbar">
            <input v-model="state.charts.page_url" placeholder="Page URL" />
            <input v-model="state.charts.platform" placeholder="Platform" style="max-width: 140px" />
            <input v-model="state.charts.symbol" placeholder="Symbol" style="max-width: 140px" />
            <input v-model="state.charts.timeframe" placeholder="Timeframe" style="max-width: 120px" />
            <button class="action primary" @click="captureChart">Capture</button>
          </div>

          <div class="card cards-grid">
            <div class="snapshot" v-for="item in state.charts.items" :key="item.id">
              <div class="title">{{ item.title }}</div>
              <div class="muted">{{ item.url }}</div>
              <div class="muted">{{ item.media_paths[0] }}</div>
              <div class="actions-row">
                <button class="action" @click="analyzeChart(item)">Analyze</button>
                <span class="badge">{{ item.analysis_status }}</span>
              </div>
            </div>
          </div>
        </section>

        <section v-else class="pane">
          <div class="toolbar">
            <input v-model="state.topic.topic_name" placeholder="Topic name" style="max-width: 220px" />
            <input v-model="state.topic.description" placeholder="Description" />
            <input v-model="state.topic.focus" placeholder="Analyze focus" style="max-width: 220px" />
            <button class="action primary" @click="createTopic">Create Topic</button>
          </div>

          <div class="two-panels">
            <div class="card list">
              <h3>Topics</h3>
              <div v-for="topic in state.topic.topics" :key="topic.id" class="item">
                <div class="title">#{{ topic.id }} {{ topic.topic_name }}</div>
                <div class="muted">{{ topic.topic_type }} · {{ topic.description }}</div>
                <div class="muted">{{ formatDateTime(topic.updated_at) }}</div>
                <button class="action" @click="analyzeTopic(topic)">Analyze</button>
              </div>
            </div>

            <div class="card list">
              <h3>Key Entities</h3>
              <div v-for="entity in state.topic.entities" :key="entity.id" class="item">
                <div class="title">{{ entity.entity_name }}</div>
                <div class="muted">reliability {{ entity.reliability_score }} · forecast {{ entity.forecast_score }}</div>
                <div class="text">{{ entity.profile_summary || 'No summary' }}</div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  `,
}).mount('#app');
