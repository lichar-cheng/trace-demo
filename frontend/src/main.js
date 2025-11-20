const { createApp, ref, reactive, onMounted, defineComponent } = Vue;

const createStore = () => {
  const posts = reactive([]);
  const logs = reactive([]);
  const sessionId = Math.random().toString(36).slice(2);
  const addPosts = (items) => {
    items.forEach(i=>{
      if(!i.url) return;
      if(!posts.find(p=>p.url===i.url)) posts.push(i);
    })
  }
  const addBrowse = (url, kol_handle) => {
    logs.push({ visited_at: new Date().toISOString(), url, kol_handle, kol_post_url: url, session_id: sessionId })
  }
  return { posts, logs, addPosts, addBrowse, sessionId }
}
const store = createStore()

const EmbeddedBrowser = defineComponent({
  name: 'EmbeddedBrowser',
  props: { startPath: { type: String, default: 'home' } },
  setup(props){
    const frameRef = ref(null);
    const storeRef = store;
    const src = ref(`/proxy/x/${props.startPath}`);
    const onMsg = (e)=>{
      const d = e.data;
      if(!d||!d.type) return;
      if(d.type==='tweets_visible'){
        const items = (d.payload?.items||[]).map(x=>({
          kol_handle: x.kol_handle||'',
          kol_name: x.kol_name||'',
          kol_avatar_url: x.kol_avatar_url||'',
          posted_at: null,
          text: x.text||'',
          image_urls: x.image_urls||[],
          likes: x.likes||0,
          retweets: x.retweets||0,
          replies: x.replies||0,
          url: x.url
        }))
        store.addPosts(items)
      }
      if(d.type==='browse'){
        const url = d.payload?.url
        store.addBrowse(url, '')
      }
    }
    onMounted(()=>{
      window.addEventListener('message', onMsg)
    })
    return { frameRef, src, store: storeRef }
  },
  template: `
    <div class="panel p-2 h-full flex flex-col">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm text-gray-600">会话: {{ store.sessionId }}</div>
        <div class="flex gap-2">
          <input class="border rounded px-2 py-1 w-96" v-model="src" />
          <button class="px-3 py-1 bg-blue-600 text-white rounded" @click="()=>{ }">跳转</button>
        </div>
      </div>
      <iframe :src="src" ref="frameRef" class="flex-1 w-full" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" ></iframe>
    </div>
  `
})

const CapturePanel = defineComponent({
  name: 'CapturePanel',
  setup(){
    return { store }
  },
  template: `
    <div class="panel p-3">
      <div class="font-semibold mb-2">采集数据</div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <div class="text-sm mb-2">帖子（{{ store.posts.length }}）</div>
          <div class="list space-y-2">
            <div v-for="p in store.posts" :key="p.url" class="p-2 border rounded">
              <div class="text-sm font-medium">{{ p.kol_handle }}</div>
              <div class="text-sm mono break-words">{{ p.url }}</div>
              <div class="text-sm text-gray-700">{{ p.text.slice(0,140) }}</div>
              <div class="text-xs text-gray-500">👍 {{ p.likes }} 🔁 {{ p.retweets }} 💬 {{ p.replies }}</div>
            </div>
          </div>
        </div>
        <div>
          <div class="text-sm mb-2">浏览记录（{{ store.logs.length }}）</div>
          <div class="list space-y-2">
            <div v-for="l in store.logs" :key="l.visited_at + l.url" class="p-2 border rounded">
              <div class="text-sm mono">{{ l.visited_at }}</div>
              <div class="text-sm break-words">{{ l.url }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})

import { api } from './services/api.js'

const App = defineComponent({
  name: 'App',
  components: { EmbeddedBrowser, CapturePanel },
  setup(){
    const storeRef = store;
    const syncing = ref(false);
    const sync = async ()=>{
      if(syncing.value) return;
      syncing.value = true;
      const posts = storeRef.posts.splice(0, storeRef.posts.length);
      const logs = storeRef.logs.splice(0, storeRef.logs.length);
      if(posts.length) await api.syncPosts(posts);
      if(logs.length) await api.syncBrowse(logs);
      syncing.value = false;
    }
    onMounted(()=>{
      setInterval(sync, 5000)
    })
    return { store: storeRef, syncing, sync }
  },
  template: `
    <div class="h-full flex flex-col">
      <header class="p-3 bg-white border-b">
        <div class="max-w-7xl mx-auto flex items-center justify-between">
          <div class="text-lg font-semibold">X 嵌入浏览与采集（Vue 3 + Python）</div>
          <div class="flex items-center gap-2">
            <button class="px-3 py-1 bg-green-600 text-white rounded" @click="sync">立即同步</button>
            <span class="text-sm" v-if="syncing">同步中…</span>
          </div>
        </div>
      </header>
      <main class="max-w-7xl mx-auto p-3 grid grid-cols-3 gap-3 flex-1 w-full">
        <div class="col-span-2 h-[78vh]"><EmbeddedBrowser/></div>
        <div class="h-[78vh]"><CapturePanel/></div>
      </main>
    </div>
  `
})

createApp(App).mount('#app')