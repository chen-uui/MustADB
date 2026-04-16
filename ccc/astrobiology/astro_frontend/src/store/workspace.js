/**
 * 统一RAG工作台状态管理
 * 完全重构版本 - 使用Vuex进行状态管理
 */

import { createStore } from 'vuex'
import { 
  TAB_TYPES, 
  WORKFLOW_STEPS, 
  WORKFLOW_STATUS, 
  PROCESSING_STATUS,
  REQUEST_STATUS 
} from '@/api/interfaces.js'

// 工作台主状态
const workspaceModule = {
  namespaced: true,
  state: {
  // 基础状态
    activeTab: TAB_TYPES.METEORITE_SEARCH,
    isLoading: false,
    error: null,
    systemStatus: {},
  
  // 工作流状态
    currentWorkflow: null,
    workflowStatus: WORKFLOW_STATUS.NOT_STARTED,
    workflowProgress: 0,
    workflowSteps: [],
  
  // 当前文档状态
    currentDocument: null,
    currentQuestion: '',
    currentResult: null,
  
  // 处理状态
    processingStatus: PROCESSING_STATUS.IDLE,
    processingProgress: 0,
    
    // 添加缺少的状态
    documents: [],
    qaHistory: [],
    extractionTasks: [],
    results: { extractedData: [] }
  },
  
  getters: {
    isWorkflowActive: (state) => 
      state.workflowStatus === WORKFLOW_STATUS.IN_PROGRESS,
    
    canSwitchTab: (state) => 
      !(state.workflowStatus === WORKFLOW_STATUS.IN_PROGRESS) || 
      state.processingStatus === PROCESSING_STATUS.IDLE,
    
    workflowStepCount: (state) => state.workflowSteps.length,
    
    completedSteps: (state) => 
      state.workflowSteps.filter(step => step.status === 'completed').length,
    
    workflowProgressPercentage: (state, getters) => 
      getters.workflowStepCount > 0 ? (getters.completedSteps / getters.workflowStepCount) * 100 : 0,
    
    // 添加缺少的getter
    activeTab: (state) => state.activeTab,
    currentDocument: (state) => state.currentDocument,
    processingStatus: (state) => state.processingStatus,
    systemStatus: (state) => state.systemStatus,
    documents: (state) => state.documents || [],
    qaHistory: (state) => state.qaHistory || [],
    extractionTasks: (state) => state.extractionTasks || [],
    results: (state) => state.results || { extractedData: [] }
  },
  
  mutations: {
    SET_ACTIVE_TAB(state, tab) {
      state.activeTab = tab
      state.error = null
    },
    
    SET_CURRENT_DOCUMENT(state, document) {
      state.currentDocument = document
    },
    
    SET_CURRENT_QUESTION(state, question) {
      state.currentQuestion = question
    },
    
    SET_CURRENT_RESULT(state, result) {
      state.currentResult = result
    },
    
    SET_LOADING(state, loading) {
      state.isLoading = loading
    },
    
    SET_ERROR(state, error) {
      state.error = error
    },
    
    CLEAR_ERROR(state) {
      state.error = null
    },
    
    START_WORKFLOW(state, workflow) {
      state.currentWorkflow = workflow
      state.workflowStatus = WORKFLOW_STATUS.IN_PROGRESS
      state.workflowProgress = 0
      state.workflowSteps = workflow.steps || []
    },
    
    UPDATE_WORKFLOW_STEP(state, { stepId, status, data }) {
      const step = state.workflowSteps.find(s => s.id === stepId)
    if (step) {
      step.status = status
      step.data = data
      step.completedAt = status === 'completed' ? new Date().toISOString() : null
    }
    },
    
    COMPLETE_WORKFLOW(state) {
      state.workflowStatus = WORKFLOW_STATUS.COMPLETED
      state.workflowProgress = 100
    },
    
    FAIL_WORKFLOW(state, error) {
      state.workflowStatus = WORKFLOW_STATUS.FAILED
      state.error = error
    },
    
    CANCEL_WORKFLOW(state) {
      state.workflowStatus = WORKFLOW_STATUS.CANCELLED
      state.currentWorkflow = null
      state.workflowSteps = []
      state.workflowProgress = 0
    },
    
    RESET_WORKFLOW(state) {
      state.currentWorkflow = null
      state.workflowStatus = WORKFLOW_STATUS.NOT_STARTED
      state.workflowSteps = []
      state.workflowProgress = 0
    },
    
    SET_PROCESSING_STATUS(state, status) {
      state.processingStatus = status
    },
    
    SET_PROCESSING_PROGRESS(state, progress) {
      state.processingProgress = progress
    },
    
    UPDATE_SYSTEM_STATUS(state, status) {
      state.systemStatus = { ...state.systemStatus, ...status }
    }
  },
  
  actions: {
    switchTab({ commit }, tab) {
      commit('SET_ACTIVE_TAB', tab)
    },
    
    setCurrentDocument({ commit }, document) {
      commit('SET_CURRENT_DOCUMENT', document)
    },
    
    setCurrentQuestion({ commit }, question) {
      commit('SET_CURRENT_QUESTION', question)
    },
    
    setCurrentResult({ commit }, result) {
      commit('SET_CURRENT_RESULT', result)
    },
    
    setLoading({ commit }, loading) {
      commit('SET_LOADING', loading)
    },
    
    setError({ commit }, error) {
      commit('SET_ERROR', error)
    },
    
    clearError({ commit }) {
      commit('CLEAR_ERROR')
    },
    
    startWorkflow({ commit }, workflow) {
      commit('START_WORKFLOW', workflow)
    },
    
    updateWorkflowStep({ commit }, { stepId, status, data }) {
      commit('UPDATE_WORKFLOW_STEP', { stepId, status, data })
    },
    
    completeWorkflow({ commit }) {
      commit('COMPLETE_WORKFLOW')
    },
    
    failWorkflow({ commit }, error) {
      commit('FAIL_WORKFLOW', error)
    },
    
    cancelWorkflow({ commit }) {
      commit('CANCEL_WORKFLOW')
    },
    
    resetWorkflow({ commit }) {
      commit('RESET_WORKFLOW')
    },
    
    setProcessingStatus({ commit }, status) {
      commit('SET_PROCESSING_STATUS', status)
    },
    
    setProcessingProgress({ commit }, progress) {
      commit('SET_PROCESSING_PROGRESS', progress)
    },
    
    updateSystemStatus({ commit }, status) {
      commit('UPDATE_SYSTEM_STATUS', status)
    },
    
    initialize({ commit }) {
      commit('RESET_WORKFLOW')
      commit('CLEAR_ERROR')
      commit('SET_LOADING', false)
    },
    
    restoreState({ commit }) {
    try {
      const savedState = localStorage.getItem('workspace-state')
      if (savedState) {
        const state = JSON.parse(savedState)
          commit('SET_ACTIVE_TAB', state.activeTab || TAB_TYPES.METEORITE_SEARCH)
          commit('SET_CURRENT_DOCUMENT', state.currentDocument)
          commit('SET_CURRENT_QUESTION', state.currentQuestion)
          commit('SET_CURRENT_RESULT', state.currentResult)
      }
    } catch (error) {
      console.error('Failed to restore workspace state:', error)
    }
    },
    
    saveState({ state }) {
      try {
        const stateToSave = {
          activeTab: state.activeTab,
          currentDocument: state.currentDocument,
          currentQuestion: state.currentQuestion,
          currentResult: state.currentResult
        }
        localStorage.setItem('workspace-state', JSON.stringify(stateToSave))
    } catch (error) {
      console.error('Failed to save workspace state:', error)
    }
  }
  }
}

// 陨石搜索状态
const meteoriteSearchModule = {
  namespaced: true,
  state: {
    searchResults: [],
    searchHistory: [],
    currentSearch: {},
    searchConfig: {},
    isLoading: false,
    error: null
  },
  
  getters: {
    searchResults: (state) => state.searchResults,
    searchHistory: (state) => state.searchHistory,
    currentSearch: (state) => state.currentSearch,
    searchConfig: (state) => state.searchConfig,
    isLoading: (state) => state.isLoading,
    error: (state) => state.error
  },
  
  mutations: {
    SET_SEARCH_RESULTS(state, results) {
      state.searchResults = results
    },
    
    ADD_SEARCH_HISTORY(state, search) {
      state.searchHistory.unshift({
      ...search,
      timestamp: new Date().toISOString()
    })
    // 保持最近20条记录
      if (state.searchHistory.length > 20) {
        state.searchHistory = state.searchHistory.slice(0, 20)
      }
    },
    
    SET_CURRENT_SEARCH(state, search) {
      state.currentSearch = search
    },
    
    SET_SEARCH_CONFIG(state, config) {
      state.searchConfig = config
    },
    
    SET_LOADING(state, loading) {
      state.isLoading = loading
    },
    
    SET_ERROR(state, error) {
      state.error = error
    },
    
    CLEAR_ERROR(state) {
      state.error = null
    }
  },
  
  actions: {
    setSearchResults({ commit }, results) {
      commit('SET_SEARCH_RESULTS', results)
    },
    
    addSearchHistory({ commit }, search) {
      commit('ADD_SEARCH_HISTORY', search)
    },
    
    setCurrentSearch({ commit }, search) {
      commit('SET_CURRENT_SEARCH', search)
    },
    
    setSearchConfig({ commit }, config) {
      commit('SET_SEARCH_CONFIG', config)
    },
    
    setLoading({ commit }, loading) {
      commit('SET_LOADING', loading)
    },
    
    setError({ commit }, error) {
      commit('SET_ERROR', error)
    },
    
    clearError({ commit }) {
      commit('CLEAR_ERROR')
    }
  }
}

// 文档管理状态
const documentManagementModule = {
  namespaced: true,
  state: {
    documents: [],
    currentDocument: null,
    uploadQueue: [],
    processingQueue: [],
    isLoading: false,
    error: null,
    pagination: {
      current_page: 1,
      page_size: 100,
      total_documents: 0,
      total_pages: 1,
      has_next: false,
      has_previous: false
    }
  },
  
  getters: {
    documents: (state) => state.documents,
    currentDocument: (state) => state.currentDocument,
    uploadQueue: (state) => state.uploadQueue,
    processingQueue: (state) => state.processingQueue,
    isLoading: (state) => state.isLoading,
    error: (state) => state.error,
    pagination: (state) => state.pagination
  },
  
  mutations: {
    ADD_DOCUMENT(state, document) {
      state.documents.unshift(document)
    },
    
    UPDATE_DOCUMENT(state, document) {
      const index = state.documents.findIndex(d => d.id === document.id)
      if (index !== -1) {
        state.documents[index] = document
      }
    },
    
    REMOVE_DOCUMENT(state, documentId) {
      state.documents = state.documents.filter(d => d.id !== documentId)
    },
    
    SET_CURRENT_DOCUMENT(state, document) {
      state.currentDocument = document
    },
    
    ADD_TO_UPLOAD_QUEUE(state, file) {
      state.uploadQueue.push({
      file,
      status: 'pending',
      progress: 0,
      id: Date.now().toString()
    })
    },
  
    UPDATE_UPLOAD_PROGRESS(state, { fileId, progress }) {
      const item = state.uploadQueue.find(item => item.id === fileId)
    if (item) {
      item.progress = progress
    }
    },
    
    REMOVE_FROM_UPLOAD_QUEUE(state, fileId) {
      state.uploadQueue = state.uploadQueue.filter(item => item.id !== fileId)
    },
    
    ADD_TO_PROCESSING_QUEUE(state, document) {
      state.processingQueue.push({
      ...document,
      status: 'processing',
      progress: 0
    })
    },
  
    UPDATE_PROCESSING_PROGRESS(state, { documentId, progress }) {
      const item = state.processingQueue.find(item => item.id === documentId)
    if (item) {
      item.progress = progress
    }
    },
    
    REMOVE_FROM_PROCESSING_QUEUE(state, documentId) {
      state.processingQueue = state.processingQueue.filter(item => item.id !== documentId)
    },
    
    SET_LOADING(state, loading) {
      state.isLoading = loading
    },
    
    SET_ERROR(state, error) {
      state.error = error
    },
    
    CLEAR_ERROR(state) {
      state.error = null
    },
    
    SET_SEARCH_RESULTS(state, results) {
      // 如果results包含documents数组，使用它；否则直接使用results
      if (results && results.documents) {
        state.documents = results.documents
        // 保存分页信息
        if (results.pagination) {
          state.pagination = results.pagination
        }
      } else if (Array.isArray(results)) {
        state.documents = results
      } else {
        state.documents = []
      }
    }
  },
  
  actions: {
    addDocument({ commit }, document) {
      commit('ADD_DOCUMENT', document)
    },
    
    updateDocument({ commit }, document) {
      commit('UPDATE_DOCUMENT', document)
    },
    
    removeDocument({ commit }, documentId) {
      commit('REMOVE_DOCUMENT', documentId)
    },
    
    setCurrentDocument({ commit }, document) {
      commit('SET_CURRENT_DOCUMENT', document)
    },
    
    addToUploadQueue({ commit }, file) {
      commit('ADD_TO_UPLOAD_QUEUE', file)
    },
    
    updateUploadProgress({ commit }, { fileId, progress }) {
      commit('UPDATE_UPLOAD_PROGRESS', { fileId, progress })
    },
    
    removeFromUploadQueue({ commit }, fileId) {
      commit('REMOVE_FROM_UPLOAD_QUEUE', fileId)
    },
    
    addToProcessingQueue({ commit }, document) {
      commit('ADD_TO_PROCESSING_QUEUE', document)
    },
    
    updateProcessingProgress({ commit }, { documentId, progress }) {
      commit('UPDATE_PROCESSING_PROGRESS', { documentId, progress })
    },
    
    removeFromProcessingQueue({ commit }, documentId) {
      commit('REMOVE_FROM_PROCESSING_QUEUE', documentId)
    },
    
    setLoading({ commit }, loading) {
      commit('SET_LOADING', loading)
    },
    
    setError({ commit }, error) {
      commit('SET_ERROR', error)
    },
    
    clearError({ commit }) {
      commit('CLEAR_ERROR')
    },
    
    setSearchResults({ commit }, results) {
      commit('SET_SEARCH_RESULTS', results)
    }
  }
}

// 智能问答状态
const intelligentQAModule = {
  namespaced: true,
  state: {
    qaHistory: [],
    currentQuestion: '',
    currentAnswer: '',
    aiStatus: 'idle',
    context: {},
    qaConfig: {},
    isLoading: false,
    error: null
  },
  
  getters: {
    qaHistory: (state) => state.qaHistory,
    currentQuestion: (state) => state.currentQuestion,
    currentAnswer: (state) => state.currentAnswer,
    aiStatus: (state) => state.aiStatus,
    context: (state) => state.context,
    qaConfig: (state) => state.qaConfig,
    isLoading: (state) => state.isLoading,
    error: (state) => state.error
  },
  
  mutations: {
    ADD_QA_HISTORY(state, qaEntry) {
      state.qaHistory.unshift({
        ...qaEntry,
        id: Date.now().toString(),
        timestamp: new Date().toISOString()
      })
    },
    
    SET_CURRENT_QUESTION(state, question) {
      state.currentQuestion = question
    },
    
    SET_CURRENT_ANSWER(state, answer) {
      state.currentAnswer = answer
    },
    
    SET_AI_STATUS(state, status) {
      state.aiStatus = status
    },
    
    UPDATE_CONTEXT(state, newContext) {
      state.context = { ...state.context, ...newContext }
    },
    
    SET_QA_CONFIG(state, config) {
      state.qaConfig = config
    },
    
    SET_LOADING(state, loading) {
      state.isLoading = loading
    },
    
    SET_ERROR(state, error) {
      state.error = error
    },
    
    CLEAR_ERROR(state) {
      state.error = null
    }
  },
  
  actions: {
    addQAHistory({ commit }, qaEntry) {
      commit('ADD_QA_HISTORY', qaEntry)
    },
    
    setCurrentQuestion({ commit }, question) {
      commit('SET_CURRENT_QUESTION', question)
    },
    
    setCurrentAnswer({ commit }, answer) {
      commit('SET_CURRENT_ANSWER', answer)
    },
    
    setAIStatus({ commit }, status) {
      commit('SET_AI_STATUS', status)
    },
    
    updateContext({ commit }, newContext) {
      commit('UPDATE_CONTEXT', newContext)
    },
    
    setQAConfig({ commit }, config) {
      commit('SET_QA_CONFIG', config)
    },
    
    setLoading({ commit }, loading) {
      commit('SET_LOADING', loading)
    },
    
    setError({ commit }, error) {
      commit('SET_ERROR', error)
    },
    
    clearError({ commit }) {
      commit('CLEAR_ERROR')
    }
  }
}

// 创建Vuex store
const store = createStore({
  modules: {
    workspace: workspaceModule,
    meteoriteSearch: meteoriteSearchModule,
    documentManagement: documentManagementModule,
    intelligentQA: intelligentQAModule
  }
})

export default store