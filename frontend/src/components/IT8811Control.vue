<template>
  <el-card class="control-card">
    <template #header>
      <div class="card-header">
        <span>IT8811控制</span>
      </div>
    </template>
    
    <el-form :model="form" label-width="120px">
      <!-- 电阻值调整 -->
      <el-form-item label="电阻值 (Ω)">
        <el-input-number 
          v-model="form.resistance" 
          :min="10" 
          :max="7500" 
          :step="10" 
          style="width: 200px;"
          @change="onResistanceChange"
        />
        <el-slider 
          v-model="form.resistance" 
          :min="10" 
          :max="7500" 
          :step="10" 
          style="width: 300px; margin-left: 20px;"
          @change="onResistanceChange"
        />
        <el-button 
          type="primary" 
          @click="setResistance"
          :loading="settingResistance"
        >
          设置电阻
        </el-button>
      </el-form-item>
      
      <!-- 输出控制 -->
      <el-form-item label="输出状态">
        <el-switch 
          v-model="form.outputEnabled" 
          active-text="ON" 
          inactive-text="OFF"
          @change="toggleOutput"
        />
        <el-tag :type="form.outputEnabled ? 'success' : 'danger'" size="small" style="margin-left: 20px;">
          {{ form.outputEnabled ? '输出开启' : '输出关闭' }}
        </el-tag>
      </el-form-item>
    </el-form>
    
    <!-- 操作日志 -->
    <el-divider>操作日志</el-divider>
    <el-scrollbar height="150px">
      <el-timeline>
        <el-timeline-item 
          v-for="(log, index) in logs" 
          :key="index"
          :type="log.type"
          :timestamp="log.time"
        >
          {{ log.message }}
        </el-timeline-item>
      </el-timeline>
    </el-scrollbar>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const form = ref({
  resistance: 7500,
  outputEnabled: false
})

const settingResistance = ref(false)
const togglingOutput = ref(false)
const logs = ref([])

// 添加日志
const addLog = (message, type = 'info') => {
  const now = new Date()
  const time = now.toLocaleTimeString()
  logs.value.unshift({ message, type, time })
  // 限制日志数量
  if (logs.value.length > 20) {
    logs.value = logs.value.slice(0, 20)
  }
}

// 电阻值变化
const onResistanceChange = (value) => {
  console.log('电阻值变化:', value)
}

// 设置电阻值
const setResistance = async () => {
  settingResistance.value = true
  try {
    const response = await axios.post('/api/it8811/resistance', {
      resistance: form.value.resistance.toString()
    })
    
    if (response.data.success) {
      ElMessage.success('电阻值设置成功')
      addLog(`电阻值设置为: ${form.value.resistance}Ω`, 'success')
    } else {
      ElMessage.error('电阻值设置失败: ' + response.data.message)
      addLog(`电阻值设置失败: ${response.data.message}`, 'danger')
    }
  } catch (error) {
    console.error('设置电阻值失败:', error)
    ElMessage.error('设置电阻值失败，请检查后端服务是否运行')
    addLog('设置电阻值失败: 后端服务未响应', 'danger')
  } finally {
    settingResistance.value = false
  }
}

// 切换输出状态
const toggleOutput = async () => {
  togglingOutput.value = true
  try {
    const state = form.value.outputEnabled ? 'ON' : 'OFF'
    const response = await axios.post('/api/it8811/output', {
      state: state
    })
    
    if (response.data.success) {
      ElMessage.success(`输出已${state === 'ON' ? '开启' : '关闭'}`)
      addLog(`输出状态: ${state}`, 'success')
    } else {
      // 恢复开关状态
      form.value.outputEnabled = !form.value.outputEnabled
      ElMessage.error(`输出${state === 'ON' ? '开启' : '关闭'}失败: ${response.data.message}`)
      addLog(`输出${state === 'ON' ? '开启' : '关闭'}失败: ${response.data.message}`, 'danger')
    }
  } catch (error) {
    console.error('切换输出状态失败:', error)
    // 恢复开关状态
    form.value.outputEnabled = !form.value.outputEnabled
    ElMessage.error('切换输出状态失败，请检查后端服务是否运行')
    addLog('切换输出状态失败: 后端服务未响应', 'danger')
  } finally {
    togglingOutput.value = false
  }
}

// 初始化
onMounted(() => {
  addLog('IT8811控制面板已加载', 'info')
})
</script>

<style scoped>
.control-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
