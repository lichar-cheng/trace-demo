const { createApp, reactive, computed, onMounted } = Vue;
import { api } from './services/api.js';

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
