<template>
  <div class="admin-login">
    <div class="login-card">
      <h2>管理员登录</h2>
      <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-button type="primary" class="login-button" @click="submit" :loading="loading">登录</el-button>
      </el-form>
      <div class="hint">仅限授权管理员访问后台</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiMethods } from '@/utils/apiClient.js'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess, getApiMessage } from '@/utils/apiResponse'

const emit = defineEmits(['login-success'])
const formRef = ref(null)
const form = ref({ username: '', password: '' })
const loading = ref(false)
const rules = {
  username: [{ required: true, message: '请输入用户名' }],
  password: [{ required: true, message: '请输入密码' }]
}

const submit = async () => {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      // 调用后端登录API
      const response = await apiMethods.post('/api/pdf/auth/login/', {
        username: form.value.username,
        password: form.value.password
      })

      const payload = ensureApiSuccess(response, '登录失败')

      if (payload.token) {
          localStorage.setItem('token', payload.token)
          localStorage.setItem('admin_logged_in', 'true')
          console.log('登录成功，token已存储:', payload.token)
          ElMessage.success(getApiMessage(payload, '登录成功'))
          emit('login-success')
      } else {
        ElMessage.error('登录失败：未收到 token')
      }
    } catch (error) {
      console.error('登录错误:', error)
      ElMessage.error(getApiErrorMessage(error, '登录失败，请检查网络连接'))
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.admin-login { display: flex; align-items: center; justify-content: center; height: 100vh; background: linear-gradient(135deg,#eef2ff,#f8fafc); }
.login-card { width: 380px; background: #fff; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,.08); padding: 24px; }
.login-card h2 { margin: 0 0 16px; font-weight: 600; color: #1e293b; text-align: center; }
.login-button { width: 100%; margin-top: 8px; }
.hint { margin-top: 12px; text-align: center; color: #64748b; font-size: 12px; }
</style>
