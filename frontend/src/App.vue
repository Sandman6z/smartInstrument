<template>
  <div class="app-container">
    <el-container>
      <el-header height="60px" class="app-header">
        <h1 class="app-title">智能仪器测试系统</h1>
      </el-header>
      
      <el-main class="app-main">
        <el-row :gutter="20">
          <el-col :span="24">
            <!-- 设备连接组件 -->
            <DeviceConnect />
          </el-col>
          
          <el-col :span="24">
            <!-- IT8811控制组件 -->
            <IT8811Control />
          </el-col>
          
          <el-col :span="24">
            <!-- 数据采集组件 -->
            <DataCollection />
          </el-col>
          
          <el-col :span="24">
            <!-- 数据显示组件 -->
            <DataDisplay />
          </el-col>
        </el-row>
      </el-main>
      
      <el-footer height="40px" class="app-footer">
        <p class="footer-text">© 2026 智能仪器测试系统</p>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import DeviceConnect from './components/DeviceConnect.vue'
import IT8811Control from './components/IT8811Control.vue'
import DataCollection from './components/DataCollection.vue'
import DataDisplay from './components/DataDisplay.vue'
import { io } from 'socket.io-client'
import { ElMessage } from 'element-plus'

// 初始化SocketIO连接
const socket = io('http://localhost:5000')

// 监听数据更新事件
socket.on('data_updated', (data) => {
  console.log('收到实时数据:', data)
  ElMessage.success('数据采集完成')
})

// 监听设备状态变化事件
socket.on('device_status_changed', (status) => {
  console.log('设备状态变化:', status)
})

// 监听连接错误
socket.on('connect_error', (error) => {
  console.error('Socket连接错误:', error)
  ElMessage.warning('无法连接到后端服务，请确保后端服务已启动')
})

onMounted(() => {
  console.log('应用已启动')
  ElMessage.info('智能仪器测试系统已启动')
})

onUnmounted(() => {
  // 断开Socket连接
  socket.disconnect()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background-color: #f5f7fa;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  background-color: #409eff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.app-title {
  font-size: 20px;
  font-weight: bold;
}

.app-main {
  padding: 20px;
  background-color: #f5f7fa;
}

.app-footer {
  background-color: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  border-top: 1px solid #e4e7ed;
}

.footer-text {
  color: #909399;
  font-size: 14px;
}
</style>
