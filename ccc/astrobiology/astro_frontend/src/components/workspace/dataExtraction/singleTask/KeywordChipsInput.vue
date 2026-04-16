<template>
  <div class="chips-input" :class="[theme, { 'dark-mode': theme === 'dark' }]" @click="focusInput">
    <div v-for="(token, index) in tokens" :key="`${token}-${index}`" class="chip">
      <span class="chip-text">{{ token }}</span>
      <button type="button" class="chip-remove" @click.stop="removeToken(index)">×</button>
    </div>
    <input
      ref="inputRef"
      v-model="draft"
      type="text"
      :placeholder="tokens.length ? '' : placeholder"
      class="chips-input-field"
      autocomplete="off"
      @keydown.enter.prevent="commitDraft"
      @keydown.backspace="handleBackspace"
      @keydown="handleKeydown"
      @blur="commitDraft(true)"
      @input="onInput"
    >
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: ''
  },
  theme: {
    type: String,
    default: 'light' // 'light' or 'dark'
  }
})

const emit = defineEmits(['update:modelValue', 'draft-change'])

const tokens = ref([...props.modelValue])
const draft = ref('')
const inputRef = ref(null)

watch(
  () => props.modelValue,
  (value) => {
    tokens.value = [...(value || [])]
  }
)

watch(draft, (value) => {
  emit('draft-change', value)
})

const updateTokens = (nextTokens) => {
  tokens.value = nextTokens
  emit('update:modelValue', [...nextTokens])
}

const commitDraft = (fromBlur = false) => {
  const value = draft.value.trim()
  if (value) {
    updateTokens([...tokens.value, value])
    draft.value = ''
  } else if (fromBlur) {
    draft.value = ''
  }
}

const removeToken = (index) => {
  const next = [...tokens.value]
  next.splice(index, 1)
  updateTokens(next)
}

const handleBackspace = () => {
  if (!draft.value && tokens.value.length) {
    const next = [...tokens.value]
    next.pop()
    updateTokens(next)
  }
}

const delimiterKeys = new Set([',', '，', ';', '；'])

const handleKeydown = (event) => {
  if (delimiterKeys.has(event.key)) {
    event.preventDefault()
    commitDraft()
  }
}

const focusInput = () => {
  inputRef.value?.focus()
}

const onInput = (event) => {
  // 确保输入正确更新
  draft.value = event.target.value
}
</script>

<style scoped>
.chips-input {
  min-height: 42px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid rgba(65, 84, 241, 0.18);
  border-radius: 12px;
  background: white;
  cursor: text;
  transition: all 0.3s ease;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: linear-gradient(120deg, rgba(95, 125, 255, 0.12), rgba(95, 196, 255, 0.18));
  color: #3c4aad;
  font-size: 0.85rem;
}

.chip-text {
  line-height: 1;
}

.chip-remove {
  border: none;
  background: transparent;
  color: #3c4aad;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0;
}

.chip-remove:hover {
  color: #1f2a7c;
}

.chips-input-field {
  flex: 1;
  min-width: 120px;
  border: none;
  outline: none;
  font-size: 0.95rem;
  padding: 4px 0;
  background: transparent;
  color: inherit;
}

.chips-input-field::placeholder {
  color: #9ca3af;
}

/* Dark Mode Styles */
.chips-input.dark-mode {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.chips-input.dark-mode:focus-within {
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
}

.chips-input.dark-mode .chip {
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.chips-input.dark-mode .chip-remove {
  color: #94a3b8;
}

.chips-input.dark-mode .chip-remove:hover {
  color: #f87171;
}

.chips-input.dark-mode .chips-input-field {
  color: #fff;
}

.chips-input.dark-mode .chips-input-field::placeholder {
  color: #64748b;
}
</style>