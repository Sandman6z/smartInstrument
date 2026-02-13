<template>
  <el-card class="collection-card">
    <template #header>
      <div class="card-header">
        <span>数据采集</span>
        <div>
          <el-button type="success" @click="saveData" :loading="savingData">
            <el-icon><Download /></el-icon>
            保存数据
          </el-button>
          <el-button type="danger" @click="clearData" :loading="clearingData" style="margin-left: 10px;">
            <el-icon><Delete /></el-icon>
            清除数据
          </el-button>
        </div>
      </div>
    </template>
    
    <div class="trigger-section">
      <el-button 
        type="primary" 
        size="large" 
        @click="manualTrigger"
        :loading="triggering"
        :disabled="!canTrigger"
        class="trigger-button"
      >
        <el-icon><Timer /></el-icon>
        手动触发记录
      </el-button>
      <el-alert
        v-if="!canTrigger"
        title="无法触发"
        type="warning"
        description="请先连接所有必要的设备"
        show-icon
        :closable="false"
        style="margin-top: 20px;"
      />
    </div>
    
    <!-- 最近采集的数据 -->
    <el-divider>最近采集数据</el-divider>
    <el-table :data="recentData" style="width: 100%">
      <el-table-column prop="time" label="时间" width="180" />
      <el-table-column prop="resistance" label="电阻 (Ω)" width="150" />
      <el-table-column prop="voltage" label="电压 (V)" width="150" />
      <el-table-column prop="current" label="电流 (A)" width="150" />
      <el-table-column label="操作">
        <template #default="scope">
          <el-button size="small" type="primary" link @click="copyData(scope.row)">
            复制
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Delete, Timer } from '@element-plus/icons-vue'

const triggering = ref(false)
const savingData = ref(false)
const clearingData = ref(false)
const recentData = ref([])

// 计算是否可以触发采集
const canTrigger = computed(() => {
  // 这里可以根据设备连接状态判断
  // 暂时返回true，实际使用时需要根据设备状态判断
  return true
})

// 手动触发数据采集
const manualTrigger = async () => {
  triggering.value = true
  try {
    const response = await axios.post('/api/data/trigger')
    if (response.data.success) {
      const data = response.data.data
      const now = new Date()
      const time = now.toLocaleString()
      
      // 添加到最近数据列表
      recentData.value.unshift({
        time: time,
        resistance: data.resistance,
        voltage: data.voltage,
        current: data.current
      })
      
      // 限制最近数据数量
      if (recentData.value.length > 10) {
        recentData.value = recentData.value.slice(0, 10)
      }
      
      ElMessage.success('数据采集成功')
    } else {
      ElMessage.error('数据采集失败: ' + response.data.message)
    }
  } catch (error) {
    console.error('数据采集失败:', error)
    ElMessage.error('数据采集失败，请检查后端服务是否运行')
  } finally {
    triggering.value = false
  }
}

// 保存数据到CSV
const saveData = async () => {
  savingData.value = true
  try {
    const response = await axios.post('/api/data/save')
    if (response.data.success) {
      ElMessage.success(response.data.message)
    } else {
      ElMessage.error('保存数据失败: ' + response.data.message)
    }
  } catch (error) {
    console.error('保存数据失败:', error)
    ElMessage.error('保存数据失败，请检查后端服务是否运行')
  } finally {
    savingData.value = false
  }
}

// 清除测试数据
const clearData = async () => {
  try {
    await ElMessageBox.confirm('确定要清除所有测试数据吗？此操作不可撤销。', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    clearingData.value = true
    const response = await axios.post('/api/data/clear')
    if (response.data.success) {
      recentData.value = []
      ElMessage.success(response.data.message)
    } else {
      ElMessage.error('清除数据失败: ' + response.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清除数据失败:', error)
      ElMessage.error('清除数据失败，请检查后端服务是否运行')
    }
  } finally {
    clearingData.value = false
  }
}

// 复制数据到剪贴板
const copyData = (row) => {
  const dataStr = `时间: ${row.time}\n电阻: ${row.resistance}Ω\n电压: ${row.voltage}V\n电流: ${row.current}A`
  navigator.clipboard.writeText(dataStr).then(() => {
    ElMessage.success('数据已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}
</script>

<style scoped>
.collection-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.trigger-section {
  text-align: center;
  padding: 30px 0;
}
.trigger-button {
  width: 300px;
  height: 80px;
  font-size: 18px;
}
</style>
