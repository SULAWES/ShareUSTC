<template>
  <div
    class="file-uploader"
    :class="{
      'is-dragover': isDragOver,
      'is-disabled': disabled
    }"
    @dragenter.prevent="handleDragEnter"
    @dragover.prevent="handleDragOver"
    @dragleave.prevent="handleDragLeave"
    @drop.prevent="handleDrop"
    @click="handleClick"
  >
    <input
      ref="fileInput"
      type="file"
      class="file-input"
      :accept="accept"
      @change="handleFileChange"
    />

    <div v-if="!selectedFile" class="upload-placeholder">
      <el-icon class="upload-icon"><Upload /></el-icon>
      <div class="upload-text">
        <span class="primary-text">点击或拖拽文件到此处上传</span>
        <span class="secondary-text">
          支持 {{ acceptedExtensions.join(', ') }} 格式，最大 {{ maxSizeMB }}MB
        </span>
      </div>
    </div>

    <div v-else class="file-selected">
      <div class="file-info">
        <el-icon class="file-icon"><Document /></el-icon>
        <div class="file-details">
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
        </div>
        <el-icon class="delete-icon" @click.stop="clearFile"><Close /></el-icon>
      </div>

      <div v-if="isUploading" class="upload-progress">
        <el-progress :percentage="uploadProgress" :stroke-width="8" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { Upload, Document, Close } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { formatFileSize, SupportedExtensions } from '../../types/resource';

const props = defineProps<{
  modelValue?: File | null;
  accept?: string;
  maxSizeMB?: number;
  disabled?: boolean;
  isUploading?: boolean;
  uploadProgress?: number;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', file: File | null): void;
  (e: 'change', file: File | null): void;
}>();

const fileInput = ref<HTMLInputElement>();
const isDragOver = ref(false);

// 支持的扩展名
const acceptedExtensions = SupportedExtensions;

// 默认 accept 值
const defaultAccept = acceptedExtensions.map(ext => `.${ext}`).join(',');
const accept = computed(() => props.accept || defaultAccept);

// 最大文件大小 (MB)
const maxSizeMB = computed(() => props.maxSizeMB || 100);

// 选中的文件
const selectedFile = computed({
  get: () => props.modelValue || null,
  set: (value) => {
    emit('update:modelValue', value);
    emit('change', value);
  }
});

// 验证文件
const validateFile = (file: File): boolean => {
  // 检查文件大小
  const maxSize = maxSizeMB.value * 1024 * 1024;
  if (file.size > maxSize) {
    ElMessage.error(`文件大小超过限制，最大支持 ${maxSizeMB.value}MB`);
    return false;
  }

  // 检查文件类型
  const ext = file.name.split('.').pop()?.toLowerCase() || '';
  if (!acceptedExtensions.includes(ext)) {
    ElMessage.error(`不支持的文件类型: .${ext}。支持: ${acceptedExtensions.join(', ')}`);
    return false;
  }

  return true;
};

// 处理文件选择
const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];

  if (file) {
    if (validateFile(file)) {
      selectedFile.value = file;
    }
  }

  // 重置 input 以便可以重复选择同一文件
  input.value = '';
};

// 处理点击
const handleClick = () => {
  if (props.disabled) return;
  fileInput.value?.click();
};

// 拖拽进入
const handleDragEnter = () => {
  if (props.disabled) return;
  isDragOver.value = true;
};

// 拖拽经过
const handleDragOver = () => {
  if (props.disabled) return;
  isDragOver.value = true;
};

// 拖拽离开
const handleDragLeave = () => {
  isDragOver.value = false;
};

// 处理拖放
const handleDrop = (event: DragEvent) => {
  if (props.disabled) return;
  isDragOver.value = false;

  const file = event.dataTransfer?.files[0];
  if (file) {
    if (validateFile(file)) {
      selectedFile.value = file;
    }
  }
};

// 清除文件
const clearFile = () => {
  selectedFile.value = null;
};
</script>

<style scoped>
.file-uploader {
  border: 2px dashed var(--el-border-color);
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background-color: var(--el-fill-color-lighter);
}

.file-uploader:hover {
  border-color: var(--el-color-primary);
}

.file-uploader.is-dragover {
  border-color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

.file-uploader.is-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.file-input {
  display: none;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon {
  font-size: 48px;
  color: var(--el-text-color-secondary);
}

.upload-text {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.primary-text {
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.secondary-text {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.file-selected {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--el-bg-color);
  border-radius: 4px;
}

.file-icon {
  font-size: 24px;
  color: var(--el-color-primary);
}

.file-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  color: var(--el-text-color-primary);
  word-break: break-all;
}

.file-size {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.delete-icon {
  font-size: 16px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  transition: color 0.3s;
}

.delete-icon:hover {
  color: var(--el-color-danger);
}

.upload-progress {
  padding: 0 8px;
}
</style>
