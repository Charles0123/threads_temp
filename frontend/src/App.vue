<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { LineChart } from 'echarts/charts'

use([CanvasRenderer, GridComponent, LegendComponent, TooltipComponent, LineChart])

interface AnalysisResponse {
  dates: string[]
  counts: number[]
  posts: Post[]
  top_engagement: Post[]
  top_likes: Post[]
}

interface Post {
  published_at: string
  text: string
  url: string
  likes: number
  engagement: number
}

interface AuthStatus {
  logged_in: boolean
  username: string | null
  profile_url: string | null
}

const keyword = ref('')
const today = new Date()
const endDate = ref(today.toISOString().slice(0, 10))
const startDate = ref(new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10))
const loading = ref(false)
const errorMessage = ref('')
const result = ref<AnalysisResponse | null>(null)
const authStatus = ref<AuthStatus>({ logged_in: false, username: null, profile_url: null })

const totalPosts = computed(() => result.value?.counts.reduce((sum, count) => sum + count, 0) ?? 0)
const peakCount = computed(() => Math.max(...(result.value?.counts ?? [0])))

async function loadAuthStatus() {
  try {
    const response = await fetch('http://localhost:8000/api/auth/status')
    if (response.ok) authStatus.value = (await response.json()) as AuthStatus
  } catch {
    authStatus.value = { logged_in: false, username: null, profile_url: null }
  }
}

onMounted(loadAuthStatus)

const chartOptions = computed(() => ({
  animationDuration: 700,
  grid: { left: 18, right: 18, top: 32, bottom: 28, containLabel: true },
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#17211f',
    borderWidth: 0,
    textStyle: { color: '#f7f5ed' },
    valueFormatter: (value: number) => `${value} 篇`,
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: result.value?.dates ?? [],
    axisLine: { lineStyle: { color: '#d8d4c8' } },
    axisLabel: { color: '#69716c' },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#ece9df' } },
    axisLabel: { color: '#69716c' },
  },
  series: [
    {
      name: '討論篇數',
      type: 'line',
      smooth: true,
      data: result.value?.counts ?? [],
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#d05d3c', width: 3 },
      itemStyle: { color: '#d05d3c', borderColor: '#fffaf0', borderWidth: 3 },
      areaStyle: { color: 'rgba(208, 93, 60, 0.12)' },
    },
  ],
}))

async function analyze() {
  const trimmedKeyword = keyword.value.trim()
  if (!trimmedKeyword || loading.value) return

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await fetch('http://localhost:8000/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        keyword: trimmedKeyword,
        start_date: startDate.value,
        end_date: endDate.value,
      }),
    })

    if (!response.ok) throw new Error('分析服務目前無法回應')
    result.value = (await response.json()) as AnalysisResponse
  } catch (error) {
    result.value = null
    errorMessage.value = error instanceof Error ? error.message : '發生未知錯誤，請稍後再試'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Threads 聲量分析首頁">
        <span class="brand-mark">T</span>
        <span>THREADS / SIGNAL</span>
      </a>
      <span class="status-dot" :class="{ 'is-authenticated': authStatus.logged_in }">
        {{ authStatus.logged_in ? `@${authStatus.username}` : '未登入 Threads' }}
      </span>
    </header>

    <section class="hero-section">
      <div class="hero-copy">
        <p class="eyebrow">SOCIAL LISTENING / 01</p>
        <h1>看見話題<br /><em>如何升溫。</em></h1>
        <p class="hero-description">輸入一個關鍵字，追蹤 Threads 上的公開討論節奏。</p>
      </div>

      <form class="search-panel" @submit.prevent="analyze">
        <label for="keyword">分析關鍵字</label>
        <div class="search-row">
          <input
            id="keyword"
            v-model="keyword"
            type="search"
            placeholder="例如：人工智慧"
            maxlength="100"
            :disabled="loading"
          />
          <button type="submit" :disabled="loading || !keyword.trim()">
            <span v-if="loading" class="spinner" aria-hidden="true"></span>
            <span>{{ loading ? '分析中' : '開始分析' }}</span>
            <span v-if="!loading" aria-hidden="true">↗</span>
          </button>
        </div>
        <div class="date-row">
          <label for="start-date">搜尋區間</label>
          <input id="start-date" v-model="startDate" type="date" :max="endDate" :disabled="loading" />
          <span>至</span>
          <input v-model="endDate" type="date" :min="startDate" :disabled="loading" aria-label="結束日期" />
        </div>
        <p class="search-hint">分析公開貼文 · 依日期統計 · 約需數十秒</p>
      </form>
    </section>

    <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
    <p v-else-if="!authStatus.logged_in" class="auth-message" role="status">
      尚未載入 Threads 登入 Session。請先執行登入指令，再重新整理此頁面。
    </p>

    <section v-if="result" class="results-section" aria-live="polite">
      <div class="results-heading">
        <div>
          <p class="eyebrow">ANALYSIS RESULT</p>
          <h2>「{{ keyword.trim() }}」的討論趨勢</h2>
        </div>
        <span class="result-date">{{ result.dates.length ? `${result.dates[0]} — ${result.dates.at(-1)}` : '沒有資料' }}</span>
      </div>

      <div v-if="result.posts.length" class="result-grid">
        <div class="chart-panel">
          <VChart class="chart" :option="chartOptions" autoresize />
        </div>
        <aside class="metrics-panel">
          <p class="metric-label">TOTAL MENTIONS</p>
          <strong>{{ totalPosts.toLocaleString() }}</strong>
          <span>篇公開貼文</span>
          <div class="metric-divider"></div>
          <p class="metric-label">PEAK DAY</p>
          <strong>{{ peakCount.toLocaleString() }}</strong>
          <span>單日最高討論量</span>
        </aside>
      </div>
      <div v-else class="empty-state">
        <strong>目前找不到相關公開貼文</strong>
        <span>換個關鍵字再試一次。</span>
      </div>

      <div v-if="result.posts.length" class="ranking-grid">
        <section class="ranking-panel">
          <div class="ranking-heading">
            <div>
              <p class="eyebrow">TOP INTERACTION</p>
              <h3>互動度最高</h3>
            </div>
            <span>前 10 篇</span>
          </div>
          <p class="ranking-note">公開頁面未提供點擊數，依可取得的互動數排序。</p>
          <ol class="post-list">
            <li v-for="post in result.top_engagement" :key="`engagement-${post.url}`">
              <a :href="post.url" target="_blank" rel="noreferrer">
                <span class="post-rank">{{ result.top_engagement.indexOf(post) + 1 }}</span>
                <span class="post-copy">{{ post.text }}</span>
                <strong>{{ post.engagement.toLocaleString() }}</strong>
              </a>
            </li>
          </ol>
        </section>

        <section class="ranking-panel">
          <div class="ranking-heading">
            <div>
              <p class="eyebrow">TOP LIKES</p>
              <h3>按讚數最高</h3>
            </div>
            <span>前 10 篇</span>
          </div>
          <p class="ranking-note">依貼文公開顯示的按讚數排序。</p>
          <ol class="post-list">
            <li v-for="post in result.top_likes" :key="`likes-${post.url}`">
              <a :href="post.url" target="_blank" rel="noreferrer">
                <span class="post-rank">{{ result.top_likes.indexOf(post) + 1 }}</span>
                <span class="post-copy">{{ post.text }}</span>
                <strong>{{ post.likes.toLocaleString() }}</strong>
              </a>
            </li>
          </ol>
        </section>
      </div>
    </section>

    <footer>THREADS KEYWORD ANALYZER <span>·</span> PUBLIC DATA ONLY</footer>
  </main>
</template>
