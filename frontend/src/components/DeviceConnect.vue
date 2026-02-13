<template>
  <el-card class="device-card">
    <template #header>
      <div class="card-header">
        <span>设备连接</span>
        <el-button type="primary" size="small" @click="scanDevices" :loading="scanning">
          <el-icon><Refresh /></el-icon>
          扫描设备
        </el-button>
      </div>
    </template>
    
    <el-form :model="form" label-width="120px">
      <!-- IT8811连接 -->
      <el-form-item label="IT8811资源">
        <el-select v-model="form.it8811Resource" placeholder="选择资源" style="width: 400px;">
          <el-option 
            v-for="device in devices" 
            :key="device" 
            :label="device" 
            :value="device"
          />
        </el-select>
        <el-button 
          type="primary" 
          @click="connectDevice('it8811')"
          :loading="loading.it8811"
        >
          {{ status.it8811.connected ? '断开' : '连接' }}
        </el-button>
        <el-tag :type="status.it8811.connected ? 'success' : 'danger'" size="small">
          {{ status.it8811.connected ? '已连接' : '未连接' }}
        </el-tag>
      </el-form-item>
      
      <!-- DMM6500连接 -->
      <el-form-item label="DMM6500资源">
        <el-select v-model="form.dmm6500Resource" placeholder="选择资源" style="width: 400px;">
          <el-option 
            v-for="device in devices" 
            :key="device" 
            :label="device" 
            :value="device"
          />
        </el-select>
        <el-button 
          type="primary" 
          @click="connectDevice('dmm6500')"
          :loading="loading.dmm6500"
        >
          {{ status.dmm6500.connected ? '断开' : '连接' }}
        </el-button>
        <el-tag :type="status.dmm6500.connected ? 'success' : 'danger'" size="small">
          {{ status.dmm6500.connected ? '已连接' : '未连接' }}
        </el-tag>
      </el-form-item>
      
      <!-- KEYSIGHT连接 -->
      <el-form-item label="KEYSIGHT资源">
        <el-select v-model="form.keysightResource" placeholder="选择资源" style="width: 400px;">
          <el-option 
            v-for="device in devices" 
            :key="device" 
            :label="device" 
            :value="device"
          />
        </el-select>
        <el-button 
          type="primary" 
          @click="connectDevice('keysight')"
          :loading="loading.keysight"
        >
          {{ status.keysight.connected ? '断开' : '连接' }}
        </el-button>
        <el-tag :type="status.keysight.connected ? 'success' : 'danger'" size="small">
          {{ status.keysight.connected ? '已连接' : '未连接' }}
        </el-tag>
      </el-form-item>
    </el-form>
    
    <!-- 设备状态信息 -->
    <el-divider>设备状态</el-divider>
    <el-descriptions :column="3" border>
      <el-descriptions-item label="IT8811">
        <el-tag :type="status.it8811.connected ? 'success' : 'danger'">
          {{ status.it8811.connected ? '已连接' : '未连接' }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="DMM6500">
        <el-tag :type="status.dmm6500.connected ? 'success' : 'danger'">
          {{ status.dmm6500.connected ? '已连接' : '未连接' }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="KEYSIGHT">
        <el-tag :type="status.keysight.connected ? 'success' : 'danger'">
          {{ status.keysight.connected ? '已连接' : '未连接' }}
        </el-tag>
      </el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

const devices = ref([])
const form = ref({
  it8811Resource: '',
  dmm6500Resource: '',
  keysightResource: ''
})
const loading = ref({
  it8811: false,
  dmm6500: false,
  keysight: false
})
const scanning = ref(false)
const status = ref({
  it8811: { connected: false },
  dmm6500: { connected: false },
  keysight: { connected: false }
})

// 扫描设备
const scanDevices = async () => {
  scanning.value = true
  try {
    const response = await axios.get('/api/devices/scan')
    if (response.data.success) {
      devices.value = response.data.devices
      // 自动选择设备
      if (response.data.auto_selected.it8811) {
        form.value.it8811Resource = response.data.auto_selected.it8811
      }
      if (response.data.auto_selected.dmm6500) {
        form.value.dmm6500Resource = response.data.auto_selected.dmm6500
      }
      if (response.data.auto_selected.keysight) {
        form.value.keysightResource = response.data.auto_selected.keysight
      }
      ElMessage.success(`扫描完成，找到 ${response.data.devices.length} 个设备`)
    } else {
      ElMessage.error('扫描设备失败: ' + response.data.message)
    }
  } catch (error) {
    console.error('扫描设备失败:', error)
    ElMessage.error('扫描设备失败，请检查后端服务是否运行')
  } finally {
    scanning.value = false
  }
}

// 连接设备
const connectDevice = async (deviceType) => {
  loading.value[deviceType] = true
  try {
    const resource = form.value[`${deviceType}Resource`]
    if (!resource) {
      ElMessage.warning('请选择设备资源')
      return
    }
    
    const action = status.value[deviceType].connected ? 'disconnect' : 'connect'
    const response = await axios.post('/api/devices/connect', {
      type: deviceType,
      resource: resource,
      action: action
    })
    
    if (response.data.success) {
      // 重新获取设备状态，确保状态准确
      await getDeviceStatus()
      ElMessage.success(response.data.message)
    } else {
      ElMessage.error(response.data.message)
    }
  } catch (error) {
    console.error('连接设备失败:', error)
    ElMessage.error('连接设备失败，请检查后端服务是否运行')
  } finally {
    loading.value[deviceType] = false
  }
}

// 获取设备状态
const getDeviceStatus = async () => {
  try {
    const response = await axios.get('/api/devices/status')
    if (response.data.success) {
      status.value = response.data.status
    }
  } catch (error) {
    console.error('获取设备状态失败:', error)
  }
}

// 初始化
onMounted(async () => {
  await scanDevices()
  await getDeviceStatus()
})
</script>

<style scoped>
.device-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
