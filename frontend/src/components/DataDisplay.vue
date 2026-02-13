<template>
  <el-card class="display-card">
    <template #header>
      <div class="card-header">
        <span>数据可视化</span>
        <el-select v-model="chartType" placeholder="选择图表类型" size="small">
          <el-option label="折线图" value="line" />
          <el-option label="柱状图" value="bar" />
          <el-option label="散点图" value="scatter" />
        </el-select>
      </div>
    </template>
    
    <!-- 图表区域 -->
    <div class="chart-container">
      <div ref="chartRef" class="chart" style="width: 100%; height: 400px;"></div>
    </div>
    
    <!-- 数据表格 -->
    <el-divider>测试数据表格</el-divider>
    <el-table :data="testData" style="width: 100%">
      <el-table-column prop="id" label="序号" width="80" />
      <el-table-column prop="resistance" label="电阻 (Ω)" width="120" />
      <el-table-column prop="voltage" label="电压 (V)" width="120" />
      <el-table-column prop="current" label="电流 (A)" width="120" />
      <el-table-column prop="power" label="功率 (W)" width="120" />
      <el-table-column prop="timestamp" label="时间" width="180" />
    </el-table>
    
    <!-- 数据统计 -->
    <el-divider>数据统计</el-divider>
    <el-descriptions :column="3" border>
      <el-descriptions-item label="总记录数">{{ testData.length }}</el-descriptions-item>
      <el-descriptions-item label="平均电压">{{ avgVoltage.toFixed(4) }} V</el-descriptions-item>
      <el-descriptions-item label="平均电流">{{ avgCurrent.toFixed(6) }} A</el-descriptions-item>
      <el-descriptions-item label="最大电阻">{{ maxResistance }} Ω</el-descriptions-item>
      <el-descriptions-item label="最小电阻">{{ minResistance }} Ω</el-descriptions-item>
      <el-descriptions-item label="总功率">{{ totalPower.toFixed(4) }} W</el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref(null)
const chartType = ref('line')
const testData = ref([])
let chart = null

// 模拟测试数据
const generateTestData = () => {
  const data = []
  for (let i = 1; i <= 20; i++) {
    const resistance = 7000 + Math.random() * 1000
    const voltage = 4.5 + Math.random() * 1
    const current = voltage / resistance
    const power = voltage * current
    const timestamp = new Date(Date.now() - (20 - i) * 60000).toLocaleString()
    
    data.push({
      id: i,
      resistance: resistance.toFixed(2),
      voltage: voltage.toFixed(4),
      current: current.toFixed(6),
      power: power.toFixed(4),
      timestamp: timestamp
    })
  }
  return data
}

// 计算统计数据
const avgVoltage = computed(() => {
  if (testData.value.length === 0) return 0
  const sum = testData.value.reduce((acc, item) => acc + parseFloat(item.voltage), 0)
  return sum / testData.value.length
})

const avgCurrent = computed(() => {
  if (testData.value.length === 0) return 0
  const sum = testData.value.reduce((acc, item) => acc + parseFloat(item.current), 0)
  return sum / testData.value.length
})

const maxResistance = computed(() => {
  if (testData.value.length === 0) return 0
  const max = Math.max(...testData.value.map(item => parseFloat(item.resistance)))
  return max.toFixed(2)
})

const minResistance = computed(() => {
  if (testData.value.length === 0) return 0
  const min = Math.min(...testData.value.map(item => parseFloat(item.resistance)))
  return min.toFixed(2)
})

const totalPower = computed(() => {
  if (testData.value.length === 0) return 0
  const sum = testData.value.reduce((acc, item) => acc + parseFloat(item.power), 0)
  return sum
})

// 初始化图表
const initChart = () => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
    updateChart()
  }
}

// 更新图表
const updateChart = () => {
  if (!chart) return
  
  const xAxisData = testData.value.map(item => item.timestamp)
  const voltageData = testData.value.map(item => parseFloat(item.voltage))
  const currentData = testData.value.map(item => parseFloat(item.current) * 1000) // 转换为mA
  const resistanceData = testData.value.map(item => parseFloat(item.resistance))
  
  const option = {
    title: {
      text: '测试数据趋势',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        let result = params[0].name + '<br/>'
        params.forEach(item => {
          let unit = ''
          if (item.seriesName === '电压') unit = 'V'
          else if (item.seriesName === '电流') unit = 'mA'
          else if (item.seriesName === '电阻') unit = 'Ω'
          result += `${item.seriesName}: ${item.value} ${unit}<br/>`
        })
        return result
      }
    },
    legend: {
      data: ['电压', '电流', '电阻'],
      top: 30
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '电压 (V)',
        position: 'left',
        axisLabel: {
          formatter: '{value} V'
        }
      },
      {
        type: 'value',
        name: '电流 (mA)',
        position: 'right',
        axisLabel: {
          formatter: '{value} mA'
        }
      },
      {
        type: 'value',
        name: '电阻 (Ω)',
        position: 'right',
        offset: 80,
        axisLabel: {
          formatter: '{value} Ω'
        }
      }
    ],
    series: [
      {
        name: '电压',
        type: chartType.value,
        data: voltageData,
        smooth: true,
        itemStyle: {
          color: '#409eff'
        }
      },
      {
        name: '电流',
        type: chartType.value,
        yAxisIndex: 1,
        data: currentData,
        smooth: true,
        itemStyle: {
          color: '#67c23a'
        }
      },
      {
        name: '电阻',
        type: chartType.value,
        yAxisIndex: 2,
        data: resistanceData,
        smooth: true,
        itemStyle: {
          color: '#e6a23c'
        }
      }
    ]
  }
  
  chart.setOption(option)
}

// 监听图表类型变化
watch(chartType, () => {
  updateChart()
})

// 监听窗口大小变化
const handleResize = () => {
  if (chart) {
    chart.resize()
  }
}

onMounted(() => {
  // 生成模拟数据
  testData.value = generateTestData()
  
  // 初始化图表
  nextTick(() => {
    initChart()
  })
  
  // 添加窗口大小变化监听
  window.addEventListener('resize', handleResize)
})

// 组件卸载时清理
const onUnmounted = () => {
  if (chart) {
    chart.dispose()
  }
  window.removeEventListener('resize', handleResize)
}
</script>

<style scoped>
.display-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.chart-container {
  margin-bottom: 20px;
}
</style>
