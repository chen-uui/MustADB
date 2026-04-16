<template>
  <div class="cosmic-chat-container">
    <!-- Glass Sidebar -->
    <aside class="chat-sidebar" :class="{ 'collapsed': isSidebarCollapsed }">
      <div class="sidebar-header">
        <button class="new-chat-btn" @click="startNewChat">
          <i class="bi bi-plus-lg"></i>
          <span v-if="!isSidebarCollapsed">New Chat</span>
        </button>
        <button class="toggle-sidebar-btn" @click="toggleSidebar">
          <i class="bi" :class="isSidebarCollapsed ? 'bi-layout-sidebar-inset' : 'bi-layout-sidebar'"></i>
        </button>
      </div>

      <div class="history-list-container">
        <div class="list-header" v-if="!isSidebarCollapsed">
          <span>History</span>
          <button class="clear-history-btn" @click="clearHistory" v-if="qaHistory.length" title="Clear All">
            <i class="bi bi-trash"></i>
          </button>
        </div>
        
        <div class="history-list">
          <div 
            v-for="item in qaHistory" 
            :key="item.id"
            class="history-item"
            @click="loadFromHistory(item)"
          >
            <i class="bi bi-chat-left-text item-icon"></i>
            <div class="item-content" v-if="!isSidebarCollapsed">
              <div class="item-question">{{ item.question }}</div>
              <div class="item-time">{{ formatTime(item.timestamp) }}</div>
            </div>
            <button 
              class="delete-item-btn" 
              @click.stop="deleteHistoryItem(item.id)"
              v-if="!isSidebarCollapsed"
            >
              <i class="bi bi-x"></i>
            </button>
          </div>
          <div v-if="qaHistory.length === 0 && !isSidebarCollapsed" class="empty-history">
            No history yet
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <div 
          class="system-status-indicator clickable" 
          :class="systemStatusColor" 
          v-if="systemStatus"
          @click="showStatusModal = true"
          title="Click for details"
        >
          <div class="status-dot"></div>
          <span v-if="!isSidebarCollapsed" class="status-text">{{ systemStatusText }}</span>
          <i v-if="!isSidebarCollapsed" class="bi bi-info-circle ms-auto" style="font-size: 0.8rem; opacity: 0.5;"></i>
        </div>
      </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="chat-main">
      <!-- Welcome View -->
      <div class="welcome-view" v-if="messages.length === 0">
        <div class="hero-content">
          <div class="hero-icon">
            <i class="bi bi-stars"></i>
          </div>
          <h1>Cosmic Intelligence</h1>
          <p>Explore the universe of Astrobiology with AI</p>
        </div>
        
        <div class="suggestion-grid">
          <div 
            v-for="(suggestion, index) in suggestionList" 
            :key="index"
            class="suggestion-card"
            @click="askSuggestion(suggestion)"
          >
            <span class="suggestion-text">{{ suggestion }}</span>
            <i class="bi bi-arrow-right-short"></i>
          </div>
        </div>
      </div>

      <!-- Message Stream -->
      <div class="messages-container" v-else ref="messagesContainer">
        <div 
          v-for="(msg, index) in messages" 
          :key="index"
          class="message-wrapper"
          :class="msg.role"
        >
          <div class="message-avatar">
            <i class="bi" :class="msg.role === 'user' ? 'bi-person-fill' : 'bi-robot'"></i>
          </div>
          
          <div class="message-content-group">
            <div class="message-bubble" :class="{ 'is-refreshing': msg.isRefreshing }">
              <div class="message-text" v-html="formatMessageText(msg.content)"></div>
              <div v-if="msg.isRefreshing" class="regen-overlay">
                <i class="bi bi-arrow-repeat spin"></i>
                <span>Refreshing...</span>
              </div>
            </div>
            
            <!-- Sources Accordion (AI only) -->
            <div class="message-sources" v-if="msg.role === 'ai' && msg.sources && msg.sources.length">
              <div class="sources-toggle" @click="msg.showSources = !msg.showSources">
                <i class="bi bi-journal-text"></i>
                <span>{{ getUsedCount(msg) }} / {{ msg.sources.length }} References</span>
                <i class="bi" :class="msg.showSources ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
              </div>
              
              <transition name="slide-fade">
                <div class="sources-list" v-if="msg.showSources">
                  <div 
                    v-for="(source, sIndex) in msg.sources" 
                    :key="sIndex"
                    class="source-item"
                    :class="{ 'used-source': source.used }"
                  >
                    <div class="source-header">
                      <span class="source-index">[{{ sIndex + 1 }}]</span>
                      <span class="source-title">{{ source.title }}</span>
                      <span class="source-score">{{ (source.score * 100).toFixed(0) }}% match</span>
                    </div>
                    <div class="source-snippet">
                      {{ source.content.substring(0, 120) }}...
                    </div>
                  </div>
                </div>
              </transition>
            </div>
            
            <div class="message-meta" v-if="msg.role === 'ai'">
              <span class="confidence-badge" :class="getConfidenceClass(msg.confidence)">
                {{ (msg.confidence * 100).toFixed(0) }}% Confidence
              </span>
              <button 
                class="regen-btn" 
                :disabled="msg.isRefreshing" 
                @click="regenerateAnswer(index)"
                title="Refresh answer"
              >
                <i class="bi" :class="msg.isRefreshing ? 'bi-arrow-repeat spin' : 'bi-arrow-clockwise'"></i>
              </button>
              <button class="copy-btn" @click="copyToClipboard(msg.content)">
                <i class="bi bi-clipboard"></i>
              </button>
            </div>
          </div>
        </div>

        <div class="typing-indicator" v-if="isAsking">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area-wrapper">
        <div class="input-capsule">
          <button class="settings-btn" @click="showSettings = !showSettings" title="Search Settings">
            <i class="bi bi-sliders"></i>
          </button>
          
          <textarea
            v-model="question"
            placeholder="Ask anything about the cosmos..."
            @keydown.enter.prevent="handleEnter"
            rows="1"
            ref="questionInput"
          ></textarea>
          
          <button 
            class="send-btn" 
            @click="askQuestion"
            :disabled="!question.trim() || isAsking"
          >
            <i class="bi" :class="isAsking ? 'bi-stop-fill' : 'bi-send-fill'"></i>
          </button>
        </div>

        <!-- Settings Popover -->
        <transition name="pop-up">
          <div class="settings-popover" v-if="showSettings">
            <div class="setting-row">
              <label>Strategy</label>
              <select v-model="selectedStrategy">
                <option value="auto">Auto</option>
                <option value="standard">Standard</option>
                <option value="multi-pass">Multi-pass</option>
              </select>
            </div>
            <div class="setting-row">
              <label>Top-K Results</label>
              <select v-model.number="topK">
                <option :value="3">3</option>
                <option :value="5">5</option>
                <option :value="10">10</option>
              </select>
            </div>
          </div>
        </transition>
      </div>
    </main>
    <!-- System Status Modal -->
    <transition name="fade">
      <div class="modal-overlay" v-if="showStatusModal" @click.self="showStatusModal = false">
        <div class="status-modal">
          <div class="modal-header">
            <h3>System Status</h3>
            <button class="close-btn" @click="showStatusModal = false"><i class="bi bi-x-lg"></i></button>
          </div>
          <div class="modal-body" v-if="systemStatus">
            <div class="status-item">
              <span class="label">LLM Service</span>
              <span class="value" :class="systemStatus.llm_connected ? 'text-green' : 'text-red'">
                {{ systemStatus.llm_connected ? 'Connected' : 'Disconnected' }}
              </span>
            </div>
            <div class="status-item">
              <span class="label">Vector Database</span>
              <span class="value" :class="systemStatus.weaviate_connected ? 'text-green' : 'text-red'">
                {{ systemStatus.weaviate_connected ? 'Online' : 'Offline' }}
              </span>
            </div>
            <div class="status-item">
              <span class="label">RAG Engine</span>
              <span class="value text-green">Active</span>
            </div>
          </div>
          <div class="modal-footer">
            <button class="refresh-btn" @click="loadSystemStatus">
              <i class="bi bi-arrow-clockwise"></i> Refresh Status
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import unifiedRAGService from '@/api/services/unifiedRAGService.js'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess } from '@/utils/apiResponse'

// State
const isSidebarCollapsed = ref(false)
const question = ref('')
const messages = ref([]) // { role: 'user'|'ai', content: string, sources?: [], confidence?: number, showSources?: boolean }
const isAsking = ref(false)
const qaHistory = ref([])
const systemStatus = ref(null)
const showSettings = ref(false)
const selectedStrategy = ref('auto')
const topK = ref(5)
const messagesContainer = ref(null)
const questionInput = ref(null)

const suggestionList = [
  'What are the key conclusions of this report?',
  'List key evidence for life on Mars',
  'Give me three most important research advances',
  'What are the main uncertainties in this topic?'
]

// Computed
const systemStatusColor = computed(() => {
  if (!systemStatus.value) return 'status-gray'
  if (systemStatus.value.llm_connected && systemStatus.value.weaviate_connected) return 'status-green'
  return 'status-red'
})

const systemStatusText = computed(() => {
  if (!systemStatus.value) return 'Connecting...'
  if (systemStatus.value.llm_connected && systemStatus.value.weaviate_connected) return 'Systems Online'
  return 'System Issues'
})

// Lifecycle
onMounted(() => {
  loadSystemStatus()
  loadHistory()
  // Auto-resize textarea
  watch(question, () => {
    if (questionInput.value) {
      questionInput.value.style.height = 'auto'
      questionInput.value.style.height = Math.min(questionInput.value.scrollHeight, 150) + 'px'
    }
  })
  consumeInitialQuestionFromUrl()
})

// Methods
const toggleSidebar = () => isSidebarCollapsed.value = !isSidebarCollapsed.value

const startNewChat = () => {
  messages.value = []
  question.value = ''
  if (window.innerWidth < 768) isSidebarCollapsed.value = true
}

const handleEnter = (e) => {
  if (!e.shiftKey) {
    askQuestion()
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const askSuggestion = (text) => {
  question.value = text
  askQuestion()
}

const consumeInitialQuestionFromUrl = () => {
  if (typeof window === 'undefined') return

  const url = new URL(window.location.href)
  const initialQuestion = (url.searchParams.get('question') || '').trim()
  if (!initialQuestion) return

  question.value = initialQuestion
  url.searchParams.delete('question')
  window.history.replaceState({}, '', url.toString())

  nextTick(() => {
    askQuestion()
  })
}

const askQuestion = async () => {
  if (!question.value.trim() && !isAsking.value) return
  if (isAsking.value) {
    // Stop generation logic (mock)
    isAsking.value = false
    return
  }

  const userQ = question.value
  messages.value.push({ role: 'user', content: userQ })
  question.value = ''
  isAsking.value = true
  scrollToBottom()

  try {
    const response = ensureApiSuccess(await unifiedRAGService.askQuestion(userQ, {
      strategy: selectedStrategy.value,
      top_k: topK.value
    }), '问答失败')

    if (response && (response.success || response.answer)) {
      const answerData = response.data || response
      const aiMsg = {
        role: 'ai',
        content: answerData.answer,
        sources: answerData.sources || [],
        confidence: answerData.confidence || 0.8,
        showSources: false,
        question: userQ,
        isRefreshing: false
      }
      messages.value.push(aiMsg)
      
      // Save to history
      addToHistory(userQ, aiMsg)
    } else {
      throw new Error('问答结果为空')
    }
  } catch (error) {
    console.error(error)
    messages.value.push({ 
      role: 'ai', 
      content: getApiErrorMessage(error, '问答失败，请稍后重试') 
    })
  } finally {
    isAsking.value = false
    scrollToBottom()
  }
}

const addToHistory = (q, aiMsg) => {
  const item = {
    id: Date.now(),
    question: q,
    answer: { ...aiMsg, question: q },
    timestamp: new Date()
  }
  qaHistory.value.unshift(item)
  if (qaHistory.value.length > 50) qaHistory.value.pop()
  localStorage.setItem('qa-history', JSON.stringify(qaHistory.value))
}

const loadHistory = () => {
  const saved = localStorage.getItem('qa-history')
  if (saved) {
    try {
      qaHistory.value = JSON.parse(saved)
    } catch (e) {
      console.error(e)
    }
  }
}

const loadFromHistory = (item) => {
  messages.value = [
    { role: 'user', content: item.question },
    { ...item.answer, role: 'ai', showSources: false, question: item.question, isRefreshing: false }
  ]
  if (window.innerWidth < 768) isSidebarCollapsed.value = true
}

const clearHistory = () => {
  ElMessageBox.confirm('确定要清空全部问答历史吗？', '清空历史', {
    type: 'warning'
  }).then(() => {
    qaHistory.value = []
    localStorage.removeItem('qa-history')
  }).catch(() => {})
}

const deleteHistoryItem = (id) => {
  qaHistory.value = qaHistory.value.filter(i => i.id !== id)
  localStorage.setItem('qa-history', JSON.stringify(qaHistory.value))
}

const loadSystemStatus = async () => {
  try {
    const resp = await unifiedRAGService.getServiceStatus()
    const payload = ensureApiSuccess(resp, '获取系统状态失败')
    systemStatus.value = payload?.data || payload || {}
  } catch (e) {
    console.error(e)
    systemStatus.value = { llm_connected: false, weaviate_connected: false }
  }
}

const formatTime = (ts) => {
  return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const formatMessageText = (text) => {
  if (!text) return ''
  // Basic markdown-like formatting
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

const getConfidenceClass = (score) => {
  const val = score > 1 ? score / 100 : score
  if (val > 0.8) return 'high-conf'
  if (val > 0.5) return 'med-conf'
  return 'low-conf'
}

const getUsedCount = (msg) => {
  if (!msg || !msg.sources) return 0
  return msg.sources.filter(s => s.used).length
}

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text)
  ElMessage.success('Copied')
}
const regenerateAnswer = async (aiIndex) => {
  const aiMsg = messages.value[aiIndex]
  if (!aiMsg || aiMsg.role !== 'ai' || aiMsg.isRefreshing) return
  
  // 找到对应的用户问题
  let userQ = aiMsg.question
  if (!userQ) {
    for (let i = aiIndex - 1; i >= 0; i -= 1) {
      if (messages.value[i].role === 'user') {
        userQ = messages.value[i].content
        break
      }
    }
  }
  if (!userQ) return

  aiMsg.isRefreshing = true
  try {
    const response = ensureApiSuccess(await unifiedRAGService.askQuestion(userQ, {
      strategy: selectedStrategy.value,
      top_k: topK.value
    }), '刷新答案失败')
    const answerData = response.data || response
    aiMsg.content = answerData.answer
    aiMsg.sources = answerData.sources || []
    aiMsg.confidence = answerData.confidence || 0.8
    aiMsg.showSources = false
    aiMsg.question = userQ
  } catch (e) {
    console.error(e)
    aiMsg.content = getApiErrorMessage(e, '刷新答案失败，请稍后重试')
  } finally {
    aiMsg.isRefreshing = false
    scrollToBottom()
  }
}
const showStatusModal = ref(false)

// ... (existing code)


</script>


<style scoped>
/* System Status Indicator Update */
.system-status-indicator {
  cursor: pointer;
  transition: background 0.2s;
  padding: 0.5rem;
  border-radius: 6px;
}

.system-status-indicator:hover {
  background: rgba(255, 255, 255, 0.05);
}

.clickable { cursor: pointer; }

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(5px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-modal {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  width: 400px;
  max-width: 90%;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.modal-header {
  padding: 1.2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: white;
}

.close-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  font-size: 1.1rem;
}
.close-btn:hover { color: white; }

.modal-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}

.status-item .label { color: rgba(255, 255, 255, 0.7); }
.status-item .value { font-weight: 600; }

.text-green { color: #22c55e; }
.text-red { color: #ef4444; }

.modal-footer {
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  justify-content: flex-end;
}

.refresh-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Container & Layout */
.cosmic-chat-container {
  display: flex;
  height: 100vh;
  background: transparent;
  color: white;
  font-family: 'Inter', sans-serif;
  overflow: hidden;
}

/* Sidebar */
.chat-sidebar {
  width: 280px;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  z-index: 10;
}

.chat-sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  padding: 1.5rem;
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.new-chat-btn {
  flex: 1;
  background: linear-gradient(135deg, #06b6d4, #3b82f6);
  border: none;
  border-radius: 8px;
  color: white;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  overflow: hidden;
}

.new-chat-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.toggle-sidebar-btn {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-sidebar.collapsed .new-chat-btn {
  width: 40px;
  padding: 0;
}

/* History List */
.history-list-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.8rem;
  margin-bottom: 0.5rem;
  padding: 0 0.5rem;
}

.clear-history-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
}

.clear-history-btn:hover { color: #ef4444; }

.history-item {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.8rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  color: rgba(255, 255, 255, 0.8);
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.item-icon {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.4);
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-question {
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-time {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.4);
}

.delete-item-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.3);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.history-item:hover .delete-item-btn {
  opacity: 1;
}

.delete-item-btn:hover { color: #ef4444; }

/* Sidebar Footer */
.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.system-status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-green .status-dot { background: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.5); }
.status-red .status-dot { background: #ef4444; }
.status-gray .status-dot { background: #64748b; }

/* Main Chat Area */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  max-width: 100%;
}

/* Welcome View */
.welcome-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
}

.hero-icon {
  font-size: 4rem;
  background: linear-gradient(135deg, #06b6d4, #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 1rem;
  filter: drop-shadow(0 0 20px rgba(56, 189, 248, 0.3));
}

.hero-content h1 {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  background: linear-gradient(to right, #fff, #94a3b8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-content p {
  color: rgba(255, 255, 255, 0.6);
  font-size: 1.1rem;
  margin-bottom: 3rem;
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  max-width: 600px;
  width: 100%;
}

.suggestion-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 1rem;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
  text-align: left;
}

.suggestion-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(56, 189, 248, 0.3);
  transform: translateY(-2px);
}

.suggestion-text {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
}

/* Messages */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  scroll-behavior: smooth;
}

.message-wrapper {
  display: flex;
  gap: 1rem;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.message-wrapper.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user .message-avatar {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.ai .message-avatar {
  background: linear-gradient(135deg, #06b6d4, #3b82f6);
  color: white;
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
}

.message-content-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 80%;
}

.message-bubble {
  padding: 1rem 1.2rem;
  border-radius: 18px;
  line-height: 1.6;
  font-size: 1rem;
  position: relative;
}
.message-bubble.is-refreshing {
  opacity: 0.6;
}

.user .message-bubble {
  background: linear-gradient(135deg, #06b6d4, #3b82f6);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 15px rgba(6, 182, 212, 0.2);
}

.ai .message-bubble {
  background: rgba(30, 41, 59, 0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
  border-bottom-left-radius: 4px;
}
.regen-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: rgba(0, 0, 0, 0.35);
  border-radius: 18px;
  color: white;
  font-size: 0.9rem;
  pointer-events: none;
}

/* Sources */
.message-sources {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.sources-toggle {
  padding: 0.6rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: background 0.2s;
}

.sources-toggle:hover {
  background: rgba(255, 255, 255, 0.05);
  color: white;
}

.sources-list {
  padding: 0.5rem;
  background: rgba(0, 0, 0, 0.2);
}

.source-item {
  padding: 0.8rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.source-item.used-source {
  background: rgba(34, 197, 94, 0.08);
  border-left: 3px solid #22c55e;
}

.source-item:last-child { border-bottom: none; }

.source-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
  font-size: 0.8rem;
}

.source-index { color: #38bdf8; font-weight: bold; }
.source-title { color: white; font-weight: 500; }
.source-score { margin-left: auto; color: #22c55e; }

.source-snippet {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  font-style: italic;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  font-size: 0.75rem;
  margin-top: 0.2rem;
}

.confidence-badge {
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
}

.high-conf { color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.3); }
.med-conf { color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
.low-conf { color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }

.copy-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
}
.copy-btn:hover { color: white; }
.regen-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
}
.regen-btn:disabled {
  color: rgba(255, 255, 255, 0.2);
  cursor: not-allowed;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 1rem;
  margin-left: 3rem;
}

.dot {
  width: 8px;
  height: 8px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* Input Area */
.input-area-wrapper {
  padding: 1.5rem 2rem 2rem;
  display: flex;
  justify-content: center;
  position: relative;
  background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%);
}

.input-capsule {
  width: 100%;
  max-width: 800px;
  background: rgba(30, 41, 59, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  padding: 0.5rem 1rem;
  display: flex;
  align-items: flex-end;
  gap: 0.8rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  transition: border-color 0.2s;
}

.input-capsule:focus-within {
  border-color: rgba(56, 189, 248, 0.5);
  box-shadow: 0 10px 30px rgba(56, 189, 248, 0.1);
}

.settings-btn, .send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  margin-bottom: 2px;
}

.settings-btn {
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
}

.settings-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.send-btn {
  background: white;
  color: #0f172a;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  background: #38bdf8;
  color: white;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

textarea {
  flex: 1;
  background: transparent;
  border: none;
  color: white;
  font-size: 1rem;
  padding: 0.6rem 0;
  resize: none;
  max-height: 150px;
  outline: none;
  font-family: inherit;
}

textarea::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

/* Settings Popover */
.settings-popover {
  position: absolute;
  bottom: 90px;
  left: 50%;
  transform: translateX(-50%);
  width: 250px;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1rem;
  z-index: 20;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
}

.setting-row {
  margin-bottom: 1rem;
}

.setting-row:last-child { margin-bottom: 0; }

.setting-row label {
  display: block;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 0.4rem;
}

.setting-row select {
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: white;
  padding: 0.4rem;
  border-radius: 6px;
  outline: none;
  cursor: pointer;
}

.setting-row select option {
  background: #0f172a;
  color: white;
}

/* Transitions */
.pop-up-enter-active, .pop-up-leave-active { transition: all 0.2s ease; }
.pop-up-enter-from, .pop-up-leave-to { opacity: 0; transform: translate(-50%, 10px); }

.slide-fade-enter-active, .slide-fade-leave-active { transition: all 0.3s ease; }
.slide-fade-enter-from, .slide-fade-leave-to { opacity: 0; transform: translateY(-10px); }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }

@media (max-width: 768px) {
  .chat-sidebar { position: absolute; height: 100%; }
  .chat-sidebar.collapsed { width: 0; border: none; }
  .suggestion-grid { grid-template-columns: 1fr; }
}
</style>
