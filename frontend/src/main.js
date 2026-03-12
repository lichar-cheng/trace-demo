const { createApp, reactive, computed, onMounted } = Vue;
import { api } from './services/api.js';

createApp({
  setup() {
    const state = reactive({
      view: 'x',
      status: '',
      loading: false,
      x: {
        posts: [],
        activeIndex: 0,
        keyword: '',
        compareInput: '',
      },
      youtube: {
        urlInput: '',
        channelName: 'manual_channel',
        items: [],
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

    const xFiltered = computed(() => {
      const key = state.x.keyword.trim().toLowerCase();
      return state.x.posts.filter((p) => !key || [p.text, p.kol_name, p.kol_handle, p.url].some((v) => (v || '').toLowerCase().includes(key)));
    });
    const xActive = computed(() => xFiltered.value[state.x.activeIndex] || null);

    const setStatus = (msg) => state.status = `[${new Date().toLocaleTimeString()}] ${msg}`;

    const safeRun = async (fn) => {
      state.loading = true;
      try {
        await fn();
      } catch (e) {
        setStatus(`失败：${e?.response?.data?.error || e.message}`);
function createStore() {
  const state = reactive({
    posts: [],
    activeIndex: 0,
    loading: false,
    filters: {
      keyword: '',
      batch: 'all',
      user: 'any',
      tags: 'all',
    },
    compareInput: '',
    status: '',
    syncing: false,
  });

  const filteredPosts = computed(() => {
    const keyword = state.filters.keyword.trim().toLowerCase();
    return state.posts.filter((p) => {
      if (!keyword) return true;
      return [p.text, p.kol_handle, p.kol_name, p.url].some((v) => (v || '').toLowerCase().includes(keyword));
    });
  });

  const activePost = computed(() => filteredPosts.value[state.activeIndex] || null);
  const totalAssets = computed(() => state.posts.length.toLocaleString());

  return { state, filteredPosts, activePost, totalAssets };
}

const store = createStore();

createApp({
  setup() {
    const { state, filteredPosts, activePost, totalAssets } = store;

    const loadPosts = async () => {
      state.loading = true;
      try {
        const { data } = await api.listPosts({ limit: 200 });
        state.posts = data || [];
        state.activeIndex = 0;
      } finally {
        state.loading = false;
      }
    };

    const loadX = async () => safeRun(async () => {
      const { data } = await api.listPosts({ limit: 300 });
      state.x.posts = data;
      state.x.activeIndex = 0;
      setStatus(`X 数据加载 ${data.length} 条`);
    });

    const xCompare = async () => safeRun(async () => {
      const urls = state.x.compareInput.split('\n').map((s) => s.trim()).filter(Boolean);
      const { data } = await api.compareUrls(urls);
      setStatus(`链接对比完成：存在 ${data.exists.length}，缺失 ${data.missing.length}`);
    });

    const xDelete = async () => {
      if (!xActive.value) return;
      await safeRun(async () => {
        await api.trashBatch({ urls: [xActive.value.url] });
        await loadX();
        setStatus('删除成功');
      });
    };

    const xPushTg = async () => {
      if (!xActive.value) return;
      await safeRun(async () => {
        await api.pushTg(xActive.value.url);
        setStatus('已标记推送 Telegram');
      });
    };

    const xExport = () => {
      const blob = new Blob([JSON.stringify(xFiltered.value, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `x-library-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      setStatus('导出完成');
    };

    const loadYoutube = async () => safeRun(async () => {
      const { data } = await api.youtubeList({ limit: 100 });
      state.youtube.items = data;
      setStatus(`YouTube 条目 ${data.length} 条`);
    });

    const importYoutube = async () => safeRun(async () => {
      const urls = state.youtube.urlInput.split('\n').map((s) => s.trim()).filter(Boolean);
      if (!urls.length) { setStatus('请输入 YouTube URL'); return; }
      const { data } = await api.youtubeImport(urls, state.youtube.channelName);
      await loadYoutube();
      setStatus(`YouTube 导入 ${data.created} 条`);
    });

    const analyzeYoutube = async (item) => safeRun(async () => {
      await api.youtubeAnalyze([item.id]);
      await loadYoutube();
      setStatus(`YouTube #${item.id} 分析完成`);
    });

    const loadCrypto = async () => safeRun(async () => {
      const { data } = await api.cryptoList({ limit: 100 });
      state.crypto.items = data;
      setStatus(`加密指标 ${data.length} 条`);
    });

    const pullCrypto = async () => safeRun(async () => {
      const payload = {
        metric_name: state.crypto.metric_name,
        symbol: state.crypto.symbol,
        market_type: state.crypto.market_type,
        interval: state.crypto.interval,
        value: Number(state.crypto.value || 0),
      };
      await api.cryptoPull(payload);
      await loadCrypto();
      setStatus('加密指标已写入');
    });

    const backfillCrypto = async () => safeRun(async () => {
      const now = new Date();
      const start = new Date(now.getTime() - 3600_000 * 4);
      await api.cryptoBackfill({
        metric_name: state.crypto.metric_name,
        symbol: state.crypto.symbol,
        market_type: state.crypto.market_type,
        interval: state.crypto.interval,
        start_time: start.toISOString(),
        end_time: now.toISOString(),
        values: [100, 120, 110, 130],
      });
      await loadCrypto();
      setStatus('历史补全写入完成');
    });

    const loadCharts = async () => safeRun(async () => {
      const { data } = await api.chartList({ limit: 100 });
      state.charts.items = data;
      setStatus(`图表快照 ${data.length} 条`);
    });

    const captureChart = async () => safeRun(async () => {
      const payload = {
        page_url: state.charts.page_url,
        platform: state.charts.platform,
        symbol: state.charts.symbol,
        timeframe: state.charts.timeframe,
        image_path: state.charts.image_path || `data/charts/snapshots/${Date.now()}.png`,
      };
      await api.chartCapture(payload);
      await loadCharts();
      setStatus('图表快照任务已创建');
    });

    const analyzeChart = async (item) => safeRun(async () => {
      await api.chartAnalyze(item.id);
      await loadCharts();
      setStatus(`图表 #${item.id} 分析完成`);
    });

    const loadTopic = async () => safeRun(async () => {
      const [{ data: topics }, { data: entities }] = await Promise.all([api.listTopics(), api.listEntities()]);
      state.topic.topics = topics;
      state.topic.entities = entities;
      setStatus(`主题 ${topics.length} 条，实体 ${entities.length} 条`);
    });

    const createTopic = async () => safeRun(async () => {
      if (!state.topic.topic_name.trim()) {
        setStatus('请输入主题名');
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
      setStatus('主题创建成功');
    });

    const analyzeTopic = async (item) => safeRun(async () => {
      await api.analyzeTopic(item.id, state.topic.focus);
      await loadTopic();
      setStatus(`主题 #${item.id} 分析完成`);
    });

    const backup = async () => safeRun(async () => {
      const { data } = await api.runBackup('data/backup');
      setStatus(`备份完成：${data.backup}`);
    });

    const switchView = async (view) => {
      state.view = view;
      if (view === 'x') await loadX();
      if (view === 'youtube') await loadYoutube();
      if (view === 'crypto') await loadCrypto();
      if (view === 'charts') await loadCharts();
      if (view === 'topic') await loadTopic();
    };

    onMounted(async () => {
      await loadX();
      await loadYoutube();
      await loadCrypto();
      await loadCharts();
      await loadTopic();
    });

    return {
      state,
      xFiltered,
      xActive,
      switchView,
      xCompare,
      xDelete,
      xPushTg,
      xExport,
      importYoutube,
      analyzeYoutube,
      pullCrypto,
      backfillCrypto,
      captureChart,
      analyzeChart,
      createTopic,
      analyzeTopic,
      backup,
    };
  },
  template: `
    <div class="app-shell">
      <aside class="side">
        <div class="logo">Knowledge Base</div>
        <button class="nav" :class="{active:state.view==='x'}" @click="switchView('x')">X Library</button>
        <button class="nav" :class="{active:state.view==='youtube'}" @click="switchView('youtube')">YouTube Library</button>
        <button class="nav" :class="{active:state.view==='crypto'}" @click="switchView('crypto')">Crypto Metrics</button>
        <button class="nav" :class="{active:state.view==='charts'}" @click="switchView('charts')">Chart Snapshots</button>
        <button class="nav" :class="{active:state.view==='topic'}" @click="switchView('topic')">Topic Intelligence</button>
        <div class="side-bottom"><button class="action full" @click="backup">Backup</button></div>
      </aside>

      <main class="main">
        <header class="header">
          <h1 v-if="state.view==='x'">X Library</h1>
          <h1 v-else-if="state.view==='youtube'">YouTube Library</h1>
          <h1 v-else-if="state.view==='crypto'">Crypto Metrics</h1>
          <h1 v-else-if="state.view==='charts'">Analysis & Snapshots</h1>
          <h1 v-else>Topic Intelligence</h1>
          <span class="status" :class="{loading: state.loading}">{{ state.loading ? 'Loading...' : state.status }}</span>
        </header>

        <section v-if="state.view==='x'" class="pane x-layout">
          <div class="toolbar">
            <input v-model="state.x.keyword" placeholder="Search by keywords, users, tags..." />
            <button class="action" @click="xExport">Export</button>
          </div>
          <div class="x-grid">
            <div class="card list">
              <div v-for="(post,idx) in xFiltered" :key="post.url || idx" class="item" :class="{active: idx===state.x.activeIndex}" @click="state.x.activeIndex=idx">
                <div class="title">{{ post.kol_name || post.kol_handle }}</div>
                <div class="muted">@{{ post.kol_handle }}</div>
                <div class="text">{{ post.text }}</div>
              </div>
            </div>
            <div class="card detail" v-if="xActive">
              <h2>{{ xActive.kol_name || xActive.kol_handle }}</h2>
              <div class="muted">{{ xActive.url }}</div>
              <div class="columns">
                <div>
                  <h4>Original</h4>
                  <p>{{ xActive.text }}</p>
                </div>
                <div>
                  <h4>Translated</h4>
                  <p>{{ xActive.translated_text || '暂无译文' }}</p>
                </div>
              </div>
              <div class="actions-row">
                <button class="action danger" @click="xDelete">Delete</button>
                <button class="action primary" @click="xPushTg">Push TG</button>
              </div>
            </div>
            <div class="card detail" v-else>请选择一条记录</div>
          </div>
          <div class="card compare">
            <textarea v-model="state.x.compareInput" placeholder="每行一个X链接"></textarea>
            <button class="action" @click="xCompare">Compare URLs</button>
          </div>
        </section>

        <section v-else-if="state.view==='youtube'" class="pane">
          <div class="toolbar">
            <input v-model="state.youtube.urlInput" placeholder="一行一个 YouTube URL" />
            <input v-model="state.youtube.channelName" placeholder="Channel Name" style="max-width:220px" />
            <button class="action primary" @click="importYoutube">Process</button>
          </div>
          <div class="metrics">
            <div class="metric"><strong>{{ state.youtube.items.length }}</strong><span>Total Videos</span></div>
            <div class="metric"><strong>{{ state.youtube.items.filter(i=>i.analysis_status!=='done').length }}</strong><span>Subtitle Scraping</span></div>
            <div class="metric"><strong>{{ state.youtube.items.filter(i=>i.analysis_status==='done').length }}</strong><span>Ready For Analysis</span></div>
          </div>
          <div class="card list">
            <div v-for="item in state.youtube.items" :key="item.id" class="item">
              <div class="title">{{ item.title }}</div>
              <div class="muted">{{ item.url }}</div>
              <div class="two-col">
                <div><h4>Cleaned Subtitles</h4><p>{{ item.content_cleaned || '待处理' }}</p></div>
                <div><h4>AI Analysis</h4><p>{{ item.analysis_result || '待分析' }}</p></div>
              </div>
              <button class="action" @click="analyzeYoutube(item)">Analyze</button>
    const syncNow = async () => {
      if (state.syncing) return;
      state.syncing = true;
      try {
        state.status = `已同步到后台：${new Date().toLocaleTimeString()}`;
      } finally {
        state.syncing = false;
      }
    };

    const compareUrls = async () => {
      const urls = state.compareInput.split('\n').map((u) => u.trim()).filter(Boolean);
      if (!urls.length) {
        state.status = '请输入至少一个链接';
        return;
      }
      const { data } = await api.compareUrls(urls);
      state.status = `对比完成：存在 ${data.exists.length}，缺失 ${data.missing.length}`;
    };

    const batchDelete = () => {
      state.status = '批量删除功能：待接入 /api/trash/batch';
    };

    const exportJson = () => {
      const blob = new Blob([JSON.stringify(filteredPosts.value, null, 2)], { type: 'application/json;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `x-library-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      state.status = '已导出当前筛选数据';
    };

    onMounted(loadPosts);

    return {
      state,
      filteredPosts,
      activePost,
      totalAssets,
      loadPosts,
      syncNow,
      compareUrls,
      batchDelete,
      exportJson,
    };
  },
  template: `
    <div class="x-app">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-title">CryptoAnalytics</div>
          <div class="brand-sub">DATA MANAGEMENT</div>
        </div>

        <nav class="menu">
          <a class="menu-item">Dashboard</a>
          <a class="menu-item active">X Library</a>
          <a class="menu-item">YouTube Library</a>
          <a class="menu-item">Crypto Metrics</a>
          <a class="menu-item">Chart Snapshots</a>
        </nav>

        <div class="sidebar-bottom">
          <a class="menu-item">Settings</a>
          <div class="plan-card">
            <div class="plan-title">PRO PLAN</div>
            <div class="plan-desc">Access advanced analytics and filters.</div>
            <button class="btn btn-primary full">Upgrade Plan</button>
          </div>
        </div>
      </aside>

      <main class="main">
        <header class="top">
          <div>
            <h1>X Library</h1>
            <p>{{ totalAssets }} total assets synced</p>
          </div>
          <div class="actions">
            <button class="btn" @click="batchDelete">Batch Delete</button>
            <button class="btn" @click="exportJson">Export</button>
            <button class="btn btn-primary">+ Add New Asset</button>
          </div>
        </header>

        <section class="filters">
          <input v-model="state.filters.keyword" placeholder="Search by keywords, users, or tags..." />
          <select v-model="state.filters.batch"><option value="all">Batch: All</option></select>
          <select v-model="state.filters.user"><option value="any">User: Any</option></select>
          <select v-model="state.filters.tags"><option value="all">Tags: All</option></select>
          <button class="btn" @click="syncNow">{{ state.syncing ? 'Syncing...' : 'Save' }}</button>
        </section>

        <section class="workspace">
          <div class="list panel">
            <div class="list-scroll" v-if="!state.loading">
              <article
                v-for="(post, idx) in filteredPosts"
                :key="post.url || idx"
                class="row"
                :class="{active: idx===state.activeIndex}"
                @click="state.activeIndex=idx"
              >
                <div class="avatar">{{ (post.kol_handle || 'U').slice(0,2).toUpperCase() }}</div>
                <div class="row-body">
                  <div class="row-head">
                    <strong>{{ post.kol_name || post.kol_handle || 'Unknown' }}</strong>
                    <span>{{ ((post.created_at || '').replace('T',' ').slice(5,16)) || 'now' }}</span>
                  </div>
                  <div class="handle">@{{ post.kol_handle || 'unknown' }}</div>
                  <div class="snippet">{{ post.text || 'No content' }}</div>
                </div>
              </article>
            </div>
            <div class="empty" v-else>Loading...</div>
          </div>
        </section>

        <section v-else-if="state.view==='crypto'" class="pane">
          <div class="toolbar">
            <input v-model="state.crypto.symbol" placeholder="Symbol" style="max-width:150px" />
            <input v-model="state.crypto.metric_name" placeholder="Metric" style="max-width:180px" />
            <input v-model="state.crypto.interval" placeholder="Interval" style="max-width:120px" />
            <input v-model="state.crypto.value" placeholder="Value" style="max-width:140px" />
            <button class="action primary" @click="pullCrypto">Fetch Metrics</button>
            <button class="action" @click="backfillCrypto">Backfill</button>
          </div>
          <div class="card cards-grid">
            <div class="snapshot" v-for="item in state.crypto.items" :key="item.id">
              <div class="title">{{ item.title }}</div>
              <div class="muted">{{ item.extra.metric_name }} · {{ item.extra.interval }}</div>
              <div class="value">{{ item.extra.value }}</div>
            </div>
          </div>
        </section>

        <section v-else-if="state.view==='charts'" class="pane">
          <div class="toolbar">
            <input v-model="state.charts.page_url" placeholder="Page URL" />
            <input v-model="state.charts.platform" placeholder="Platform" style="max-width:140px" />
            <input v-model="state.charts.symbol" placeholder="Symbol" style="max-width:140px" />
            <input v-model="state.charts.timeframe" placeholder="Timeframe" style="max-width:120px" />
            <button class="action primary" @click="captureChart">Capture</button>
          </div>
          <div class="card cards-grid">
            <div class="snapshot" v-for="item in state.charts.items" :key="item.id">
              <div class="title">{{ item.title }}</div>
              <div class="muted">{{ item.url }}</div>
              <div class="muted">{{ item.media_paths[0] }}</div>
              <div class="actions-row"><button class="action" @click="analyzeChart(item)">Analyze</button><span>{{ item.analysis_status }}</span></div>
            </div>
          </div>
        </section>

        <section v-else class="pane">
          <div class="toolbar">
            <input v-model="state.topic.topic_name" placeholder="Topic name" style="max-width:220px" />
            <input v-model="state.topic.description" placeholder="Description" />
            <input v-model="state.topic.focus" placeholder="Analyze focus" style="max-width:220px" />
            <button class="action primary" @click="createTopic">Create Topic</button>
          </div>
          <div class="two-panels">
            <div class="card list">
              <h3>Topics</h3>
              <div v-for="t in state.topic.topics" :key="t.id" class="item">
                <div class="title">#{{ t.id }} {{ t.topic_name }}</div>
                <div class="muted">{{ t.topic_type }} · {{ t.description }}</div>
                <button class="action" @click="analyzeTopic(t)">Analyze</button>
              </div>
            </div>
            <div class="card list">
              <h3>Key Entities</h3>
              <div v-for="e in state.topic.entities" :key="e.id" class="item">
                <div class="title">{{ e.entity_name }}</div>
                <div class="muted">reliability {{ e.reliability_score }} · forecast {{ e.forecast_score }}</div>
                <div class="text">{{ e.profile_summary || '暂无画像摘要' }}</div>
              </div>
            </div>
          </div>

          <div class="detail panel" v-if="activePost">
            <div class="detail-head">
              <div class="profile">
                <div class="big-avatar">{{ (activePost.kol_handle || 'U').slice(0,2).toUpperCase() }}</div>
                <div>
                  <h2>{{ activePost.kol_name || activePost.kol_handle }}</h2>
                  <div class="handle">@{{ activePost.kol_handle }} · {{ activePost.posted_at || activePost.created_at }}</div>
                  <div class="badges">
                    <span class="badge green">Pushed to Telegram</span>
                    <span class="badge purple">Stored</span>
                  </div>
                </div>
              </div>
              <div class="icons">⋯</div>
            </div>

            <div class="texts">
              <div class="text-card">
                <h4>ORIGINAL TEXT</h4>
                <p>{{ activePost.text }}</p>
              </div>
              <div class="text-card">
                <h4>TRANSLATED TEXT (AI)</h4>
                <p>{{ activePost.translated_text || '暂无译文' }}</p>
              </div>
            </div>

            <div class="media" v-if="activePost.image_urls && activePost.image_urls.length">
              <h4>MEDIA ATTACHMENTS</h4>
              <div class="media-grid">
                <img v-for="img in activePost.image_urls" :src="img" :key="img" alt="media" />
              </div>
            </div>

            <div class="tags">
              <span class="tag">#Bitcoin</span>
              <span class="tag">#TechnicalAnalysis</span>
              <span class="tag">#Bullish</span>
            </div>

            <div class="stats">❤ {{ activePost.likes || 0 }} · 🔁 {{ activePost.retweets || 0 }} · 👁 {{ activePost.replies || 0 }}</div>

            <div class="footer-actions">
              <button class="btn btn-danger">Delete</button>
              <button class="btn">Edit Post</button>
              <button class="btn btn-primary flex1">Push to Telegram Channel</button>
            </div>
          </div>

          <div class="detail panel empty" v-else>No post selected</div>
        </section>

        <section class="utility panel">
          <div class="utility-title">URL 对比工具</div>
          <textarea v-model="state.compareInput" placeholder="每行一个 X 帖子链接"></textarea>
          <button class="btn" @click="compareUrls">执行对比</button>
          <span class="status">{{ state.status }}</span>
        </section>
      </main>
    </div>
  `,
}).mount('#app');
