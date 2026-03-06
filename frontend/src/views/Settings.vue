<template>
  <div class="settings-page">
    <div class="settings-container">
      <h1 class="page-title">设置</h1>

      <div class="settings-sections">
        <!-- 界面设置 -->
        <section class="settings-section">
          <h2 class="section-title">
            <el-icon><Setting /></el-icon>
            界面设置
          </h2>

          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-label">首页用户指南弹窗</div>
              <div class="setting-desc">
                进入首页时显示用户指南
              </div>
            </div>
            <div class="setting-control">
              <el-switch
                v-model="showUserGuide"
                active-text="显示"
                inactive-text="隐藏"
                @change="handleUserGuideChange"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-label">资源页面指南弹窗</div>
              <div class="setting-desc">
                进入资源列表页面时显示使用指南
              </div>
            </div>
            <div class="setting-control">
              <el-switch
                v-model="showResourceGuide"
                active-text="显示"
                inactive-text="隐藏"
                @change="handleResourceGuideChange"
              />
            </div>
          </div>
        </section>

        <!-- 缓存管理 -->
        <section class="settings-section">
          <h2 class="section-title">
            <el-icon><Collection /></el-icon>
            本地缓存管理
            <el-tag v-if="cacheStats.totalEntries > 0" type="info" size="small">
              {{ cacheStats.totalEntries }} 个文件
            </el-tag>
          </h2>

          <div class="cache-content">
            <!-- 缓存统计 -->
            <div class="cache-stats">
              <div class="stat-item">
                <div class="stat-value">{{ formatSize(cacheStats.totalSize) }}</div>
                <div class="stat-label">缓存占用</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ cacheStats.totalEntries }}</div>
                <div class="stat-label">缓存文件数</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ formatDuration(cacheAge) }}</div>
                <div class="stat-label">最旧缓存</div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="cache-actions">
              <el-button
                type="primary"
                :disabled="cacheStats.totalEntries === 0"
                @click="handleClearExpired"
                :loading="clearingExpired"
              >
                <el-icon><Timer /></el-icon>
                清理过期缓存
              </el-button>

              <el-button
                type="danger"
                plain
                :disabled="cacheStats.totalEntries === 0"
                @click="handleClearAll"
                :loading="clearingAll"
              >
                <el-icon><Delete /></el-icon>
                清空所有缓存
              </el-button>

              <el-button @click="refreshStats" :loading="loading">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>

            <!-- 缓存说明 -->
            <div class="cache-info">
              <el-alert type="info" :closable="false">
                <template #title>缓存说明</template>
                <ul>
                  <li>预览和下载的资源会自动缓存到本地浏览器</li>
                  <li>缓存有效期为 24 小时，过期后会自动清理</li>
                  <li>单个文件最大缓存 100MB，总缓存上限 1GB</li>
                  <li>缓存可以减少网络请求，加快资源访问速度</li>
                </ul>
              </el-alert>
            </div>
          </div>
        </section>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { Collection, Timer, Delete, Refresh, Setting } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { resourceCache, type CacheStats } from '../utils/resourceCache';
import logger from '../utils/logger';

// 用户指南弹窗 LocalStorage 键名
const GUIDE_MODAL_KEY = 'userGuideModalClosed';
const RESOURCE_GUIDE_MODAL_KEY = 'resourceGuideModalClosed';

// 缓存状态
const loading = ref(false);
const clearingExpired = ref(false);
const clearingAll = ref(false);
const cacheStats = ref<CacheStats>({
  totalEntries: 0,
  totalSize: 0,
  oldestEntry: 0,
});

const cacheAge = computed(() => {
  if (!cacheStats.value.oldestEntry) return 0;
  return Date.now() - cacheStats.value.oldestEntry;
});

// 格式化文件大小
const formatSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + units[i];
};

// 格式化时长
const formatDuration = (ms: number): string => {
  if (ms === 0) return '-';
  const minutes = Math.floor(ms / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days} 天`;
  if (hours > 0) return `${hours} 小时`;
  if (minutes > 0) return `${minutes} 分钟`;
  return '刚刚';
};

// 刷新统计信息
const refreshStats = async () => {
  loading.value = true;
  try {
    cacheStats.value = await resourceCache.getStats();
  } catch (error) {
    ElMessage.error('获取缓存信息失败');
  } finally {
    loading.value = false;
  }
};

// 清理过期缓存
const handleClearExpired = async () => {
  clearingExpired.value = true;
  try {
    const count = await resourceCache.clearExpired();
    ElMessage.success(`已清理 ${count} 个过期缓存`);
    await refreshStats();
  } catch (error) {
    ElMessage.error('清理失败');
  } finally {
    clearingExpired.value = false;
  }
};

// 清空所有缓存
const handleClearAll = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有本地缓存吗？这将删除所有已缓存的资源文件，下次访问需要重新下载。',
      '确认清空',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );

    clearingAll.value = true;
    await resourceCache.clearAll();
    ElMessage.success('已清空所有缓存');
    await refreshStats();
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败');
    }
  } finally {
    clearingAll.value = false;
  }
};

onMounted(() => {
  refreshStats();
  loadUserGuideSetting();
  loadResourceGuideSetting();
});

// 用户指南设置
const showUserGuide = ref(true);
const showResourceGuide = ref(true);

// 加载用户指南设置
const loadUserGuideSetting = () => {
  try {
    const stored = localStorage.getItem(GUIDE_MODAL_KEY);
    if (stored) {
      const data = JSON.parse(stored);
      // 如果设置了永久关闭，则开关为 false（不显示）
      showUserGuide.value = !data.permanent;
    } else {
      // 没有设置时默认显示
      showUserGuide.value = true;
    }
  } catch (e) {
    logger.warn('[Settings]', 'Failed to parse user guide modal setting:', e);
    showUserGuide.value = true;
  }
};

// 加载资源页面指南设置
const loadResourceGuideSetting = () => {
  try {
    const stored = localStorage.getItem(RESOURCE_GUIDE_MODAL_KEY);
    if (stored) {
      const data = JSON.parse(stored);
      // 如果设置了永久关闭，则开关为 false（不显示）
      showResourceGuide.value = !data.permanent;
    } else {
      // 没有设置时默认显示
      showResourceGuide.value = true;
    }
  } catch (e) {
    logger.warn('[Settings]', 'Failed to parse resource guide modal setting:', e);
    showResourceGuide.value = true;
  }
};

// 处理用户指南设置变化
const handleUserGuideChange = (value: boolean) => {
  try {
    if (value) {
      // 开启显示：清除永久关闭设置
      localStorage.removeItem(GUIDE_MODAL_KEY);
      ElMessage.success('已开启首页用户指南弹窗');
    } else {
      // 关闭显示：设置永久关闭
      localStorage.setItem(GUIDE_MODAL_KEY, JSON.stringify({
        permanent: true,
        timestamp: Date.now()
      }));
      ElMessage.success('已永久关闭首页用户指南弹窗');
    }
  } catch (e) {
    logger.error('[Settings]', 'Failed to save user guide modal setting:', e);
    ElMessage.error('设置保存失败');
  }
};

// 处理资源页面指南设置变化
const handleResourceGuideChange = (value: boolean) => {
  try {
    if (value) {
      // 开启显示：清除永久关闭设置
      localStorage.removeItem(RESOURCE_GUIDE_MODAL_KEY);
      ElMessage.success('已开启资源页面指南弹窗');
    } else {
      // 关闭显示：设置永久关闭
      localStorage.setItem(RESOURCE_GUIDE_MODAL_KEY, JSON.stringify({
        permanent: true,
        timestamp: Date.now()
      }));
      ElMessage.success('已永久关闭资源页面指南弹窗');
    }
  } catch (e) {
    logger.error('[Settings]', 'Failed to save resource guide modal setting:', e);
    ElMessage.error('设置保存失败');
  }
};
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  background-color: #f5f7fa;
  padding: 40px 20px;
}

.settings-container {
  max-width: 800px;
  margin: 0 auto;
}

.page-title {
  margin: 0 0 32px;
  font-size: 28px;
  color: #303133;
  font-weight: 600;
}

.settings-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.section-title {
  margin: 0 0 24px;
  font-size: 18px;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.section-title .el-icon {
  color: #409eff;
}

.section-title .el-tag {
  margin-left: auto;
  font-weight: normal;
}

/* 设置项样式 */
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #ebeef5;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-info {
  flex: 1;
  padding-right: 24px;
}

.setting-label {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
}

.setting-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}

.setting-control {
  flex-shrink: 0;
}

/* 缓存内容区域 - 无内边框设计 */
.cache-content {
  padding: 0;
}

/* 缓存统计 */
.cache-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

/* 操作按钮 */
.cache-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

/* 缓存说明 */
.cache-info {
  margin-top: 8px;
}

.cache-info ul {
  margin: 8px 0 0;
  padding-left: 20px;
}

.cache-info li {
  margin: 4px 0;
  line-height: 1.6;
  color: #606266;
}

/* 响应式 */
@media (max-width: 768px) {
  .settings-page {
    padding: 20px 16px;
  }

  .page-title {
    font-size: 24px;
    margin-bottom: 20px;
  }

  .settings-section {
    padding: 16px;
  }

  .cache-stats {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }

  .stat-value {
    font-size: 24px;
  }

  .cache-actions {
    flex-direction: column;
  }

  .cache-actions .el-button {
    width: 100%;
  }

  .setting-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .setting-info {
    padding-right: 0;
  }

  .setting-control {
    width: 100%;
  }

  .setting-control :deep(.el-switch) {
    width: 100%;
  }
}
</style>
