<template>
  <div class="mineral-associations">
    <div class="associations-header">
      <h3>🔬 矿物-有机质关联分析</h3>
      <div class="associations-summary" v-if="associations.length > 0">
        共发现 {{ associations.length }} 个关联
      </div>
    </div>

    <div v-if="associations.length === 0" class="no-associations">
      <div class="no-associations-content">
        <span class="icon">🔍</span>
        <p>暂无矿物关联数据</p>
      </div>
    </div>

    <div v-else class="associations-list">
      <div 
        v-for="(association, index) in associations" 
        :key="index"
        class="association-card"
        :class="{ 'expanded': expandedCards.has(index) }"
      >
        <div class="association-header" @click="toggleCard(index)">
          <div class="mineral-info">
            <span class="mineral-icon">🪨</span>
            <h4 class="mineral-name">{{ association.mineral }}</h4>
            <span class="association-type">{{ association.association_type }}</span>
          </div>
          <div class="toggle-icon">
            {{ expandedCards.has(index) ? '−' : '+' }}
          </div>
        </div>

        <div class="association-content" v-if="expandedCards.has(index)">
          <!-- 有机化合物 -->
          <div class="compounds-section">
            <h5>🧬 关联的有机化合物</h5>
            <div class="compounds-tags">
              <span 
                v-for="compound in association.organic_compounds" 
                :key="compound"
                class="compound-tag"
              >
                {{ compound }}
              </span>
            </div>
          </div>

          <!-- 关联描述 -->
          <div class="description-section" v-if="association.description">
            <h5>📝 关联描述</h5>
            <p class="description-text">{{ association.description }}</p>
          </div>

          <!-- 实验证据 -->
          <div class="evidence-section" v-if="association.evidence">
            <h5>🔬 实验证据</h5>
            <p class="evidence-text">{{ association.evidence }}</p>
          </div>

          <!-- 科学意义 -->
          <div class="significance-section" v-if="association.significance">
            <h5>💡 科学意义</h5>
            <p class="significance-text">{{ association.significance }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 关联类型统计 -->
    <div class="association-stats" v-if="associationStats.length > 0">
      <h4>📊 关联类型分布</h4>
      <div class="stats-grid">
        <div 
          v-for="stat in associationStats" 
          :key="stat.type"
          class="stat-item"
        >
          <span class="stat-type">{{ stat.type }}</span>
          <span class="stat-count">{{ stat.count }}</span>
          <div class="stat-bar">
            <div 
              class="stat-fill" 
              :style="{ width: `${(stat.count / maxCount) * 100}%` }"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  associations: {
    type: Array,
    default: () => []
  },
  meteoriteName: {
    type: String,
    default: ''
  }
})

const expandedCards = ref(new Set())

// 计算关联类型统计
const associationStats = computed(() => {
  if (!props.associations || props.associations.length === 0) {
    return []
  }

  const typeCount = {}
  props.associations.forEach(assoc => {
    const type = assoc.association_type || 'Unknown'
    typeCount[type] = (typeCount[type] || 0) + 1
  })

  return Object.entries(typeCount)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
})

const maxCount = computed(() => {
  return Math.max(...associationStats.value.map(stat => stat.count), 1)
})

// 方法
const toggleCard = (index) => {
  if (expandedCards.value.has(index)) {
    expandedCards.value.delete(index)
  } else {
    expandedCards.value.add(index)
  }
  // 触发响应式更新
  expandedCards.value = new Set(expandedCards.value)
}

const expandAll = () => {
  expandedCards.value = new Set(props.associations.map((_, index) => index))
}

const collapseAll = () => {
  expandedCards.value = new Set()
}

// 监听associations变化，重置展开状态
watch(() => props.associations, () => {
  expandedCards.value = new Set()
}, { deep: true })

// 暴露方法给父组件
defineExpose({
  expandAll,
  collapseAll
})
</script>

<style scoped>
.mineral-associations {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 15px;
  padding: 1.5rem;
  margin: 1rem 0;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.associations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.associations-header h3 {
  color: white;
  margin: 0;
  font-size: 1.3rem;
  font-weight: 600;
}

.associations-summary {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.25rem 0.75rem;
  border-radius: 15px;
}

.no-associations {
  text-align: center;
  padding: 2rem;
}

.no-associations-content {
  color: rgba(255, 255, 255, 0.6);
}

.no-associations-content .icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 0.5rem;
}

.associations-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.association-card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
  overflow: hidden;
}

.association-card:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
}

.association-card.expanded {
  background: rgba(255, 255, 255, 0.15);
}

.association-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.association-header:hover {
  background: rgba(255, 255, 255, 0.05);
}

.mineral-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.mineral-icon {
  font-size: 1.5rem;
}

.mineral-name {
  color: white;
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.association-type {
  background: linear-gradient(135deg, #3fbbc0, #1071fb);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 15px;
  font-size: 0.8rem;
  font-weight: 600;
}

.toggle-icon {
  color: rgba(255, 255, 255, 0.8);
  font-size: 1.5rem;
  font-weight: 600;
  transition: transform 0.3s ease;
}

.association-card.expanded .toggle-icon {
  transform: rotate(180deg);
}

.association-content {
  padding: 0 1.5rem 1.5rem 1.5rem;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 500px;
  }
}

.compounds-section,
.description-section,
.evidence-section,
.significance-section {
  margin-bottom: 1rem;
}

.compounds-section:last-child,
.description-section:last-child,
.evidence-section:last-child,
.significance-section:last-child {
  margin-bottom: 0;
}

.compounds-section h5,
.description-section h5,
.evidence-section h5,
.significance-section h5 {
  color: #ffd700;
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  font-weight: 600;
}

.compounds-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.compound-tag {
  background: rgba(63, 187, 192, 0.2);
  color: #3fbbc0;
  padding: 0.25rem 0.75rem;
  border-radius: 15px;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid rgba(63, 187, 192, 0.3);
}

.description-text,
.evidence-text,
.significance-text {
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.6;
  margin: 0;
  font-size: 0.9rem;
}

.association-stats {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.association-stats h4 {
  color: white;
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0;
}

.stat-type {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
  min-width: 120px;
}

.stat-count {
  color: white;
  font-weight: 600;
  font-size: 0.9rem;
  min-width: 30px;
  text-align: right;
}

.stat-bar {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.stat-fill {
  height: 100%;
  background: linear-gradient(90deg, #3fbbc0, #1071fb);
  border-radius: 4px;
  transition: width 0.3s ease;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .mineral-associations {
    padding: 1rem;
  }
  
  .associations-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .association-header {
    padding: 0.75rem 1rem;
  }
  
  .association-content {
    padding: 0 1rem 1rem 1rem;
  }
  
  .mineral-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .stat-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .stat-bar {
    width: 100%;
  }
}
</style>