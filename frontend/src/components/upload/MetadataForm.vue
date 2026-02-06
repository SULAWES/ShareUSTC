<template>
  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    label-position="top"
    class="metadata-form"
  >
    <el-form-item label="资源标题" prop="title">
      <el-input
        v-model="form.title"
        placeholder="请输入资源标题"
        maxlength="255"
        show-word-limit
      />
    </el-form-item>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-form-item label="适用课程" prop="courseName">
          <el-input
            v-model="form.courseName"
            placeholder="例如：高等数学A"
          />
        </el-form-item>
      </el-col>

      <el-col :span="12">
        <el-form-item label="资源分类" prop="category">
          <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
            <el-option
              v-for="(label, value) in ResourceCategoryLabels"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>
      </el-col>
    </el-row>

    <el-form-item label="标签">
      <el-select
        v-model="form.tags"
        multiple
        filterable
        allow-create
        placeholder="请输入标签（最多10个）"
        style="width: 100%"
        :multiple-limit="10"
      >
        <el-option
          v-for="tag in commonTags"
          :key="tag"
          :label="tag"
          :value="tag"
        />
      </el-select>
      <div class="form-tip">输入后按回车添加标签，常用标签：{{ commonTags.join('、') }}</div>
    </el-form-item>

    <el-form-item label="资源描述">
      <el-input
        v-model="form.description"
        type="textarea"
        :rows="4"
        placeholder="描述资源内容、用途等信息（可选）"
      />
    </el-form-item>

    <el-form-item v-if="resourceType" label="资源类型">
      <el-tag :type="getResourceTypeTagType(resourceType)">
        {{ ResourceTypeLabels[resourceType] || resourceType }}
      </el-tag>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import {
  ResourceCategoryLabels,
  ResourceTypeLabels,
  type ResourceCategoryType,
  type ResourceTypeType
} from '../../types/resource';

interface FormData {
  title: string;
  courseName: string;
  category: ResourceCategoryType;
  tags: string[];
  description: string;
}

const props = defineProps<{
  modelValue: FormData;
  resourceType?: ResourceTypeType;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: FormData): void;
}>();

const formRef = ref<FormInstance>();

const form = reactive<FormData>({
  title: props.modelValue.title || '',
  courseName: props.modelValue.courseName || '',
  category: props.modelValue.category || 'other',
  tags: props.modelValue.tags || [],
  description: props.modelValue.description || ''
});

// 常用标签
const commonTags = ['期末考试', '期中考试', '作业答案', '笔记', '复习', '重点', '真题'];

// 表单验证规则
const rules: FormRules = {
  title: [
    { required: true, message: '请输入资源标题', trigger: 'blur' },
    { min: 1, max: 255, message: '标题长度在1-255个字符之间', trigger: 'blur' }
  ],
  category: [
    { required: true, message: '请选择资源分类', trigger: 'change' }
  ]
};

// 获取资源类型标签类型
const getResourceTypeTagType = (type: ResourceTypeType) => {
  const typeMap: Record<string, string> = {
    pdf: 'danger',
    ppt: 'warning',
    pptx: 'warning',
    doc: 'primary',
    docx: 'primary',
    web_markdown: 'success',
    zip: 'info'
  };
  return typeMap[type] || 'info';
};

// 监听表单变化
watch(
  () => ({ ...form }),
  (newValue) => {
    emit('update:modelValue', newValue);
  },
  { deep: true }
);

// 监听 props 变化
watch(
  () => props.modelValue,
  (newValue) => {
    form.title = newValue.title || '';
    form.courseName = newValue.courseName || '';
    form.category = newValue.category || 'other';
    form.tags = newValue.tags || [];
    form.description = newValue.description || '';
  },
  { deep: true }
);

// 验证表单
const validate = async () => {
  if (!formRef.value) return false;
  try {
    await formRef.value.validate();
    return true;
  } catch {
    return false;
  }
};

// 重置表单
const resetFields = () => {
  formRef.value?.resetFields();
};

defineExpose({
  validate,
  resetFields,
  form
});
</script>

<style scoped>
.metadata-form {
  padding: 20px 0;
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}
</style>
