<template>
  <div class="hello">
    <h1>{{ message }}</h1>
    <button @click="fetchHello">调用后端</button>
    <p v-if="backendMessage">{{ backendMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue' // ✅ 正确导入

const message = ref<string>('Hello Vue + TypeScript!')
const backendMessage = ref<string>('')

const fetchHello = async () => {
  try {
    const res = await fetch('http://localhost:8080/api/hello')
    const data: { message: string } = await res.json()
    backendMessage.value = data.message
  } catch (err) {
    backendMessage.value = '连接失败: ' + (err as Error).message
  }
}
</script>

<style scoped>
.hello {
  text-align: center;
  padding: 50px;
}
button {
  margin-top: 20px;
  padding: 10px 20px;
  font-size: 16px;
}
</style>