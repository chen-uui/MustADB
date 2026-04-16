<template>
  <div class="validation-results-display">
    <div v-if="!data || data.length === 0" class="no-data">
      <el-empty description="暂无验证结果数据" />
    </div>
    
    <div v-else class="data-content">
      <!-- 验证概览 -->
      <el-card class="overview-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><PieChart /></el-icon>
            <span>验证概览</span>
          </div>
        </template>
        
        <div class="overview-content">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic title="总检查项" :value="totalChecks" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="通过检查" :value="passedChecks" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="通过率" :value="passRate" suffix="%" />
            </el-col>
          </el-row>
          
          <div class="overall-confidence">
            <el-progress
              :percentage="overallConfidence"
              :status="getConfidenceStatus(overallConfidence)"
              :show-text="true"
            >
              <template #default="{ percentage }">
                <span class="percentage-value">整体置信度: {{ percentage }}%</span>
              </template>
            </el-progress>
          </div>
        </div>
      </el-card>

      <!-- 验证详情 -->
      <el-card class="details-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>验证详情</span>
          </div>
        </template>
        
        <div class="details-content">
          <el-collapse v-model="activeCollapse">
            <el-collapse-item
              v-for="(check, index) in data"
              :key="index"
              :name="index"
              class="validation-item"
            >
              <template #title>
                <div class="validation-title">
                  <el-icon>
                    <component :is="getCheckIcon(check.passed)" />
                  </el-icon>
                  <span class="check-name">{{ getCheckName(check.check_name) }}</span>
                  <el-tag
                    :type="check.passed ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ check.passed ? '通过' : '失败' }}
                  </el-tag>
                  <el-tag
                    type="info"
                    size="small"
                  >
                    置信度: {{ (check.confidence * 100).toFixed(1) }}%
                  </el-tag>
                </div>
              </template>
              
              <div class="validation-content">
                <div class="validation-message">
                  <el-alert
                    :title="check.message"
                    :type="check.passed ? 'success' : 'error'"
                    :closable="false"
                    show-icon
                  />
                </div>
                
                <div v-if="check.details" class="validation-details">
                  <h4>详细信息:</h4>
                  <pre>{{ JSON.stringify(check.details, null, 2) }}</pre>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-card>

      <!-- 验证建议 -->
      <el-card v-if="validationSuggestions.length > 0" class="suggestions-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Lightbulb /></el-icon>
            <span>改进建议</span>
          </div>
        </template>
        
        <div class="suggestions-content">
          <el-alert
            v-for="(suggestion, index) in validationSuggestions"
            :key="index"
            :title="suggestion"
            type="info"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { 
  PieChart, Document, Lightbulb, Check, Close, Warning 
} from '@element-plus/icons-vue'

// 定义props
const props = defineProps({
  data: {
    type: Array,
    default: () => []
  }
})

// 响应式数据
const activeCollapse = ref([])

// 计算属性
const totalChecks = computed(() => props.data.length)
const passedChecks = computed(() => props.data.filter(check => check.passed).length)
const passRate = computed(() => 
  totalChecks.value > 0 ? Math.round((passedChecks.value / totalChecks.value) * 100) : 0
)
const overallConfidence = computed(() => {
  if (props.data.length === 0) return 0
  const totalConfidence = props.data.reduce((sum, check) => sum + check.confidence, 0)
  return Math.round((totalConfidence / props.data.length) * 100)
})

// 验证建议
const validationSuggestions = computed(() => {
  const suggestions = []
  
  props.data.forEach(check => {
    if (!check.passed) {
      switch (check.check_name) {
        case 'meteorite_completeness':
          suggestions.push('建议补充陨石的基本信息，如名称、分类等')
          break
        case 'organic_completeness':
          suggestions.push('建议提供更详细的有机化合物信息')
          break
        case 'meteorite_classification':
          suggestions.push('建议使用标准的陨石分类术语')
          break
        case 'organic_consistency':
          suggestions.push('建议检查有机化合物的科学准确性')
          break
        case 'reference_format':
          suggestions.push('建议规范参考文献格式')
          break
        default:
          suggestions.push(`建议改进${getCheckName(check.check_name)}`)
      }
    }
  })
  
  return [...new Set(suggestions)] // 去重
})

// 获取检查图标
const getCheckIcon = (passed) => {
  return passed ? Check : Close
}

// 获取检查名称
const getCheckName = (checkName) => {
  const nameMap = {
    'meteorite_completeness': '陨石数据完整性',
    'organic_completeness': '有机化合物完整性',
    'insights_completeness': '科学洞察完整性',
    'references_completeness': '参考文献完整性',
    'meteorite_classification': '陨石分类科学性',
    'organic_consistency': '有机化合物一致性',
    'mineral_consistency': '矿物关系一致性',
    'reference_format': '参考文献格式',
    'reference_quantity': '参考文献数量',
    'data_types': '数据类型',
    'data_ranges': '数据范围'
  }
  return nameMap[checkName] || checkName
}

// 获取置信度状态
const getConfidenceStatus = (confidence) => {
  if (confidence >= 80) return 'success'
  if (confidence >= 60) return 'warning'
  return 'exception'
}
</script>

<style scoped>
.validation-results-display {
  padding: 20px;
}

.no-data {
  text-align: center;
  padding: 40px;
}

.data-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-card,
.details-card,
.suggestions-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  color: #2c3e50;
}

.overview-content {
  padding: 20px;
}

.overall-confidence {
  margin-top: 20px;
}

.percentage-value {
  font-weight: bold;
}

.details-content {
  padding: 20px;
}

.validation-item {
  margin-bottom: 10px;
}

.validation-title {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.check-name {
  flex: 1;
  font-weight: bold;
}

.validation-content {
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.validation-message {
  margin-bottom: 15px;
}

.validation-details {
  margin-top: 15px;
}

.validation-details h4 {
  margin-bottom: 10px;
  color: #2c3e50;
}

.validation-details pre {
  background-color: #fff;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  font-size: 12px;
  overflow-x: auto;
}

.suggestions-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.el-statistic {
  text-align: center;
}

.el-progress {
  margin-top: 10px;
}

.el-tag {
  margin: 2px;
}

.el-alert {
  margin: 5px 0;
}
</style>
