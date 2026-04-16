<template>
  <div class="meteorite-search">
    <!-- 头部区域 -->
    <div class="search-header">
      <h1>Intelligent Search</h1>
      <p>Multi-dimensional Filtering • Precision Targeting • Scientific Exploration</p>
    </div>

    <!-- 筛选控制区域 -->
    <div class="search-controls">
      <!-- 筛选类型选择卡片 -->
      <div class="filter-cards">
        <div 
          v-for="filter in filterTypes" 
          :key="filter.id"
          class="filter-card"
          :class="{ active: activeFilters.has(filter.id) }"
          @click="toggleFilter(filter.id)"
        >
          <div class="card-icon">
            <i :class="filter.icon"></i>
          </div>
          <span class="card-label">{{ filter.label }}</span>
          <div class="active-indicator"></div>
        </div>
      </div>

      <!-- 动态输入区域 -->
      <transition-group name="staggered-fade" tag="div" class="active-inputs-container">
        <!-- Meteorite Name -->
        <div v-if="activeFilters.has('name')" key="name" class="input-wrapper">
          <div class="input-label">
            <i class="bi bi-gem"></i> Meteorite Name
          </div>
          <KeywordChipsInput 
            v-model="searchCriteria.names"
            theme="dark"
            placeholder="Enter meteorite name (Press Enter)..." 
          />
        </div>

        <!-- Classification -->
        <div v-if="activeFilters.has('class')" key="class" class="input-wrapper">
          <div class="input-label">
            <i class="bi bi-diagram-3"></i> Classification
          </div>
          <MultiSelect 
            v-model="searchCriteria.classes" 
            :options="classificationOptions"
            theme="dark"
            placeholder="Select classification..."
          />
        </div>

        <!-- Location -->
        <div v-if="activeFilters.has('location')" key="location" class="input-wrapper">
          <div class="input-label">
            <i class="bi bi-geo-alt"></i> Discovery Location
          </div>
          <KeywordChipsInput 
            v-model="searchCriteria.locations"
            theme="dark"
            placeholder="Enter location..." 
          />
        </div>

        <!-- Source -->
        <div v-if="activeFilters.has('source')" key="source" class="input-wrapper">
          <div class="input-label">
            <i class="bi bi-globe2"></i> Origin Source
          </div>
          <MultiSelect 
            v-model="searchCriteria.sources" 
            :options="sourceOptions"
            theme="dark"
            placeholder="Select source..."
          />
        </div>

        <!-- Organic Compounds -->
        <div v-if="activeFilters.has('organic')" key="organic" class="input-wrapper">
          <div class="input-label">
            <i class="bi bi-virus"></i> Organic Compounds
          </div>
          <MultiSelect 
            v-model="searchCriteria.organics" 
            :options="organicOptions"
            theme="dark"
            placeholder="Select compounds..."
          />
        </div>
      </transition-group>

      <!-- 操作按钮 -->
      <div class="search-actions">
        <button 
          class="action-btn search-btn" 
          @click="performSearch"
          :disabled="isSearching"
        >
          <i class="bi" :class="isSearching ? 'bi-hourglass-split' : 'bi-search'"></i>
          {{ isSearching ? 'Searching...' : 'Start Search' }}
        </button>
        <button 
          class="action-btn clear-btn" 
          @click="clearAll"
          :disabled="activeFilters.size === 0 && !hasCriteria"
        >
          <i class="bi bi-trash"></i> Clear All
        </button>
      </div>
    </div>

    <!-- 搜索结果区域 -->
    <div class="results-section" v-if="hasSearched">
      <div class="results-header">
        <h3>Search Results <span class="count">({{ searchResults.length }})</span></h3>
        <div class="results-meta">
          <label>Show:</label>
          <select v-model="pageSize" class="page-size-select">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </div>
      </div>

      <div v-if="searchResults.length === 0" class="no-results">
        <i class="bi bi-inbox"></i>
        <p>No matching meteorite data found</p>
      </div>

      <div v-else class="results-grid">
        <div 
          v-for="meteorite in searchResults" 
          :key="meteorite.id"
          class="meteorite-card"
        >
          <div class="meteorite-header">
            <h4>{{ meteorite.name }}</h4>
            <span class="classification-tag">{{ meteorite.classification }}</span>
          </div>
          
          <div class="meteorite-body">
            <div class="info-row">
              <span class="label"><i class="bi bi-geo-alt"></i> Location:</span>
              <span class="value">{{ meteorite.location }}</span>
            </div>
            <div class="info-row">
              <span class="label"><i class="bi bi-calendar"></i> Year:</span>
              <span class="value">{{ meteorite.year }}</span>
            </div>
            <div class="info-row">
              <span class="label"><i class="bi bi-hdd"></i> Mass:</span>
              <span class="value">{{ meteorite.mass }}</span>
            </div>
            
            <div class="compounds-preview" v-if="meteorite.organic_compounds && meteorite.organic_compounds.length">
              <span class="label"><i class="bi bi-virus"></i> Organics:</span>
              <div class="tags">
                <span v-for="c in meteorite.organic_compounds.slice(0, 3)" :key="c" class="compound-tag">{{ c }}</span>
                <span v-if="meteorite.organic_compounds.length > 3" class="more-tag">+{{ meteorite.organic_compounds.length - 3 }}</span>
              </div>
            </div>
          </div>

          <div class="meteorite-footer">
            <button class="detail-btn" @click="viewDetails(meteorite)">
              View Details <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <transition name="fade">
      <div v-if="showDetailModal && selectedMeteorite" class="detail-modal-overlay" @click.self="closeDetailModal">
        <div class="detail-modal">
          <div class="detail-modal-header">
            <h3>{{ selectedMeteorite.name }}</h3>
            <button class="detail-modal-close" @click="closeDetailModal">
              <i class="bi bi-x-lg"></i>
            </button>
          </div>
          <div class="detail-modal-body">
            <div class="detail-row">
              <span class="detail-label">Classification</span>
              <span class="detail-value">{{ selectedMeteorite.classification || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Location</span>
              <span class="detail-value">{{ selectedMeteorite.location || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Year</span>
              <span class="detail-value">{{ selectedMeteorite.year || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Mass</span>
              <span class="detail-value">{{ selectedMeteorite.mass || '-' }}</span>
            </div>
            <div v-if="selectedMeteorite.organic_compounds?.length" class="detail-section">
              <h4>Organic Compounds</h4>
              <div class="detail-tags">
                <span v-for="compound in selectedMeteorite.organic_compounds" :key="compound" class="compound-tag">
                  {{ compound }}
                </span>
              </div>
            </div>
          </div>
          <div class="detail-modal-footer">
            <button class="action-btn clear-btn" @click="closeDetailModal">Close</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import MultiSelect from '@/components/MultiSelect.vue'
import KeywordChipsInput from '@/components/workspace/dataExtraction/singleTask/KeywordChipsInput.vue'

// Filter Types Definition
const filterTypes = [
  { id: 'name', label: 'Meteorite Name', icon: 'bi bi-gem' },
  { id: 'class', label: 'Classification', icon: 'bi bi-diagram-3' },
  { id: 'location', label: 'Discovery Location', icon: 'bi bi-geo-alt' },
  { id: 'source', label: 'Origin Source', icon: 'bi bi-globe2' },
  { id: 'organic', label: 'Organic Compounds', icon: 'bi bi-virus' }
]

// 状态
const activeFilters = ref(new Set()) // 默认不选中任何筛选项
const isSearching = ref(false)
const hasSearched = ref(false)
const pageSize = ref(20)
const showDetailModal = ref(false)
const selectedMeteorite = ref(null)

// 搜索条件
const searchCriteria = reactive({
  names: [],
  classes: [],
  locations: [],
  sources: [],
  organics: []
})

// 选项数据 (Mock)
const classificationOptions = [
  { label: 'Chondrite', value: 'Chondrite' },
  { label: 'Carbonaceous Chondrite', value: 'Carbonaceous Chondrite' },
  { label: 'Achondrite', value: 'Achondrite' },
  { label: 'Iron Meteorite', value: 'Iron' },
  { label: 'Stony-Iron Meteorite', value: 'Stony-Iron' },
  { label: 'Martian Meteorite', value: 'Martian' },
  { label: 'Lunar Meteorite', value: 'Lunar' }
]

const sourceOptions = [
  { label: 'Antarctica', value: 'Antarctica' },
  { label: 'Sahara Desert', value: 'Sahara' },
  { label: 'United States', value: 'USA' },
  { label: 'Australia', value: 'Australia' },
  { label: 'China', value: 'China' }
]

const organicOptions = [
  { label: 'Amino Acids', value: 'Amino Acids' },
  { label: 'Polycyclic Aromatic Hydrocarbons (PAHs)', value: 'PAHs' },
  { label: 'Carboxylic Acids', value: 'Carboxylic Acids' },
  { label: 'Sugars', value: 'Sugars' },
  { label: 'Nucleobases', value: 'Nucleobases' }
]

// 模拟结果数据
const mockResults = [
  {
    id: 1,
    name: 'Murchison',
    classification: 'CM2 Carbonaceous Chondrite',
    location: 'Victoria, Australia',
    year: '1969',
    mass: '100 kg',
    organic_compounds: ['Amino Acids', 'PAHs', 'Carboxylic Acids', 'Purines', 'Pyrimidines']
  },
  {
    id: 2,
    name: 'Allende',
    classification: 'CV3 Carbonaceous Chondrite',
    location: 'Chihuahua, Mexico',
    year: '1969',
    mass: '2000 kg',
    organic_compounds: ['Fullerenes', 'Amino Acids']
  },
  {
    id: 3,
    name: 'Tagish Lake',
    classification: 'C2-ung Carbonaceous Chondrite',
    location: 'British Columbia, Canada',
    year: '2000',
    mass: '10 kg',
    organic_compounds: ['Formic Acid', 'Acetic Acid']
  },
  {
    id: 4,
    name: 'Orgueil',
    classification: 'CI1 Carbonaceous Chondrite',
    location: 'Tarn-et-Garonne, France',
    year: '1864',
    mass: '14 kg',
    organic_compounds: ['Amino Acids', 'Sugars']
  }
]

const searchResults = ref([])

// 计算属性
const hasCriteria = computed(() => {
  return searchCriteria.names.length > 0 ||
         searchCriteria.classes.length > 0 ||
         searchCriteria.locations.length > 0 ||
         searchCriteria.sources.length > 0 ||
         searchCriteria.organics.length > 0
})

// 方法
const toggleFilter = (id) => {
  if (activeFilters.value.has(id)) {
    activeFilters.value.delete(id)
    // 清空对应的数据
    switch(id) {
      case 'name': searchCriteria.names = []; break;
      case 'class': searchCriteria.classes = []; break;
      case 'location': searchCriteria.locations = []; break;
      case 'source': searchCriteria.sources = []; break;
      case 'organic': searchCriteria.organics = []; break;
    }
  } else {
    activeFilters.value.add(id)
  }
}

const performSearch = async () => {
  isSearching.value = true
  // 模拟API调用延迟
  await new Promise(resolve => setTimeout(resolve, 800))
  
  // 简单的本地过滤逻辑 (Mock)
  searchResults.value = mockResults.filter(item => {
    // 如果没有选中任何条件，返回所有 (或者返回空，看需求，这里返回所有方便演示)
    if (!hasCriteria.value) return true
    
    let match = true
    
    if (searchCriteria.names.length > 0) {
      const nameMatch = searchCriteria.names.some(n => item.name.toLowerCase().includes(n.toLowerCase()))
      if (!nameMatch) match = false
    }
    
    if (match && searchCriteria.classes.length > 0) {
      const classMatch = searchCriteria.classes.some(c => item.classification.includes(c))
      if (!classMatch) match = false
    }
    
    if (match && searchCriteria.locations.length > 0) {
      const locMatch = searchCriteria.locations.some(l => item.location.toLowerCase().includes(l.toLowerCase()))
      if (!locMatch) match = false
    }
    
    // Source 和 Organic 逻辑类似...
    
    return match
  })
  
  hasSearched.value = true
  isSearching.value = false
}

const clearAll = () => {
  activeFilters.value.clear()
  searchCriteria.names = []
  searchCriteria.classes = []
  searchCriteria.locations = []
  searchCriteria.sources = []
  searchCriteria.organics = []
  hasSearched.value = false
  searchResults.value = []
}

const viewDetails = (meteorite) => {
  selectedMeteorite.value = meteorite
  showDetailModal.value = true
}

const closeDetailModal = () => {
  showDetailModal.value = false
  selectedMeteorite.value = null
}
</script>

<style scoped>
.meteorite-search {
  min-height: 100vh;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  color: white;
}

/* 头部样式 */
.search-header {
  text-align: center;
  margin-bottom: 3rem;
  animation: fadeInDown 0.8s ease;
}

.search-header h1 {
  font-size: 3.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 0.5rem;
  letter-spacing: -0.02em;
  text-shadow: 0 0 30px rgba(56, 189, 248, 0.3);
}

.search-header p {
  color: rgba(255, 255, 255, 0.6);
  font-size: 1.1rem;
  letter-spacing: 0.2em;
}

/* 筛选卡片样式 */
.filter-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.filter-card {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.2rem;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.filter-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(255, 255, 255, 0.1), transparent 70%);
  opacity: 0;
  transition: opacity 0.4s ease;
}

.filter-card:hover::before {
  opacity: 1;
}

.filter-card:hover {
  background: rgba(30, 41, 59, 0.8);
  transform: translateY(-8px) scale(1.02);
  border-color: rgba(56, 189, 248, 0.4);
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.3);
}

.filter-card.active {
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.9));
  border-color: #38bdf8;
  box-shadow: 0 0 30px rgba(56, 189, 248, 0.2), inset 0 0 20px rgba(56, 189, 248, 0.1);
}

.card-icon {
  font-size: 2.5rem;
  color: rgba(255, 255, 255, 0.6);
  transition: all 0.4s ease;
  background: rgba(255, 255, 255, 0.05);
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.filter-card:hover .card-icon {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transform: scale(1.1) rotate(5deg);
}

.filter-card.active .card-icon {
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
  color: white;
  border-color: transparent;
  box-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
  transform: scale(1.1);
}

.card-label {
  font-weight: 600;
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 0.02em;
  z-index: 1;
}

.filter-card.active .card-label {
  color: white;
  text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
}

.active-indicator {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #0ea5e9, #818cf8, #c084fc);
  transform: scaleX(0);
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 -2px 10px rgba(56, 189, 248, 0.5);
}

/* 输入区域样式 */
.active-inputs-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
  position: relative;
  z-index: 2;
}

.detail-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.72);
  backdrop-filter: blur(6px);
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.detail-modal {
  width: min(640px, 100%);
  background: rgba(15, 23, 42, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}

.detail-modal-header,
.detail-modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.detail-modal-footer {
  border-bottom: none;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  justify-content: flex-end;
}

.detail-modal-body {
  padding: 1.25rem;
  display: grid;
  gap: 0.9rem;
}

.detail-modal-close {
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
}

.detail-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 0.75rem;
  align-items: start;
}

.detail-label {
  color: rgba(255, 255, 255, 0.55);
  font-size: 0.9rem;
}

.detail-value {
  color: #fff;
}

.detail-section h4 {
  margin: 0 0 0.75rem;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.input-wrapper {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1.5rem;
  backdrop-filter: blur(8px);
  animation: fadeIn 0.3s ease;
}

.input-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #38bdf8;
  font-weight: 600;
  margin-bottom: 1rem;
}

/* 操作按钮样式 */
.search-actions {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin-bottom: 4rem;
  position: relative;
  z-index: 1;
}

.action-btn {
  padding: 0.8rem 2.5rem;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.search-btn {
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  border: none;
  color: white;
  box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);
}

.search-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(6, 182, 212, 0.4);
}

.search-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  filter: grayscale(0.5);
}

.clear-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.7);
}

.clear-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

/* 结果区域样式 */
.results-section {
  animation: slideUp 0.5s ease;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.results-header h3 {
  font-size: 1.5rem;
  color: white;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.count {
  color: #38bdf8;
  font-size: 1.2rem;
}

.results-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: rgba(255, 255, 255, 0.7);
}

.page-size-select {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 0.3rem 0.8rem;
  border-radius: 6px;
  outline: none;
}

.no-results {
  text-align: center;
  padding: 4rem;
  color: rgba(255, 255, 255, 0.5);
}

.no-results i {
  font-size: 3rem;
  margin-bottom: 1rem;
  display: block;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.meteorite-card {
  background: rgba(30, 41, 59, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 1.5rem;
  transition: all 0.3s ease;
}

.meteorite-card:hover {
  transform: translateY(-4px);
  border-color: rgba(56, 189, 248, 0.3);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.meteorite-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.meteorite-header h4 {
  font-size: 1.2rem;
  color: white;
  font-weight: 700;
  margin: 0;
}

.classification-tag {
  background: rgba(56, 189, 248, 0.1);
  color: #38bdf8;
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
  font-size: 0.8rem;
  border: 1px solid rgba(56, 189, 248, 0.2);
}

.meteorite-body {
  margin-bottom: 1.5rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.info-row .label {
  color: rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.info-row .value {
  color: rgba(255, 255, 255, 0.9);
}

.compounds-preview {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.compound-tag {
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  padding: 0.1rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.more-tag {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.75rem;
  padding: 0.1rem 0.5rem;
}

.detail-btn {
  width: 100%;
  padding: 0.8rem;
  background: rgba(255, 255, 255, 0.05);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
}

.detail-btn:hover {
  background: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
}

/* 动画 */
@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 列表过渡动画 */
.staggered-fade-enter-active,
.staggered-fade-leave-active {
  transition: all 0.4s ease;
}
.staggered-fade-enter-from,
.staggered-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
