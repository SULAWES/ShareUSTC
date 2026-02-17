<template>
  <div class="course-management">
    <div class="page-header">
      <h1>课程管理</h1>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>添加课程
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filterSemester" placeholder="选择学期" clearable style="width: 150px">
        <el-option
          v-for="opt in SemesterOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-select v-model="filterIsActive" placeholder="状态" clearable style="width: 120px">
        <el-option label="有效" :value="true" />
        <el-option label="无效" :value="false" />
      </el-select>
      <el-button @click="handleSearch">筛选</el-button>
      <el-button @click="resetFilter">重置</el-button>
    </div>

    <!-- 数据表格 -->
    <el-table :data="courses" v-loading="loading" border>
      <el-table-column prop="sn" label="编号" width="80" />
      <el-table-column prop="name" label="课程名称" min-width="200" />
      <el-table-column prop="semester" label="开课学期" width="120">
        <template #default="{ row }">
          {{ row.semester || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="credits" label="学分" width="100">
        <template #default="{ row }">
          {{ row.credits !== undefined && row.credits !== null ? row.credits : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="isActive" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.isActive ? 'success' : 'info'">
            {{ row.isActive ? '有效' : '无效' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.createdAt) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-switch
            v-model="row.isActive"
            size="small"
            @change="(val: boolean) => handleStatusChange(row, val)"
            style="margin-left: 8px"
          />
          <el-button size="small" type="danger" @click="handleDelete(row)" style="margin-left: 8px">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="perPage"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 添加/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑课程' : '添加课程'"
      width="500px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="课程名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入课程名称" />
        </el-form-item>
        <el-form-item label="开课学期" prop="semester">
          <el-select v-model="form.semester" placeholder="选择学期（选填）" clearable style="width: 100%">
            <el-option
              v-for="opt in SemesterOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="学分" prop="credits">
          <el-input-number
            v-model="form.credits"
            :min="0"
            :max="20"
            :precision="1"
            :step="0.5"
            placeholder="选填"
            style="width: 150px"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEditing ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import { getCourseList, createCourse, updateCourse, updateCourseStatus, deleteCourse } from '@/api/admin';
import { SemesterOptions } from '@/types/course';
import type { CourseListItem, CreateCourseRequest, UpdateCourseRequest } from '@/types/course';

const loading = ref(false);
const submitting = ref(false);
const courses = ref<CourseListItem[]>([]);
const total = ref(0);
const page = ref(1);
const perPage = ref(20);

// 筛选
const filterSemester = ref('');
const filterIsActive = ref<boolean | undefined>(undefined);

// 弹窗
const dialogVisible = ref(false);
const isEditing = ref(false);
const editingSn = ref<number | null>(null);
const formRef = ref();
const form = ref({
  name: '',
  semester: '',
  credits: undefined as number | undefined
});

const rules = {
  name: [{ required: true, message: '请输入课程名称', trigger: 'blur' }]
};


// 获取课程列表
const fetchCourses = async () => {
  loading.value = true;
  try {
    const res = await getCourseList({
      page: page.value,
      perPage: perPage.value,
      semester: filterSemester.value || undefined,
      isActive: filterIsActive.value
    });
    courses.value = res.courses;
    total.value = res.total;
  } catch (error) {
    ElMessage.error('获取课程列表失败');
  } finally {
    loading.value = false;
  }
};

// 添加课程
const handleAdd = () => {
  isEditing.value = false;
  editingSn.value = null;
  form.value = { name: '', semester: '', credits: undefined };
  dialogVisible.value = true;
};

// 编辑课程
const handleEdit = (row: CourseListItem) => {
  isEditing.value = true;
  editingSn.value = row.sn;
  form.value = {
    name: row.name,
    semester: row.semester || '',
    credits: row.credits
  };
  dialogVisible.value = true;
};

// 提交表单
const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    const data: any = {
      name: form.value.name.trim(),
      semester: form.value.semester || undefined,
      credits: form.value.credits
    };

    if (isEditing.value && editingSn.value) {
      await updateCourse(editingSn.value, data as UpdateCourseRequest);
      ElMessage.success('课程信息已更新');
    } else {
      await createCourse(data as CreateCourseRequest);
      ElMessage.success('课程已添加');
    }
    dialogVisible.value = false;
    fetchCourses();
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败');
  } finally {
    submitting.value = false;
  }
};

// 状态切换
const handleStatusChange = async (row: CourseListItem, val: boolean) => {
  try {
    await updateCourseStatus(row.sn, val);
    ElMessage.success(val ? '课程已启用' : '课程已禁用');
  } catch (error) {
    row.isActive = !val; // 回滚
    ElMessage.error('操作失败');
  }
};

// 删除课程
const handleDelete = async (row: CourseListItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除课程 "${row.name}" 吗？`,
      '确认删除',
      { type: 'warning' }
    );
    await deleteCourse(row.sn);
    ElMessage.success('课程已删除');
    fetchCourses();
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败');
    }
  }
};

// 筛选
const handleSearch = () => {
  page.value = 1;
  fetchCourses();
};

// 重置筛选
const resetFilter = () => {
  filterSemester.value = '';
  filterIsActive.value = undefined;
  page.value = 1;
  fetchCourses();
};

// 分页
const handleSizeChange = (val: number) => {
  perPage.value = val;
  page.value = 1;
  fetchCourses();
};

const handlePageChange = (val: number) => {
  page.value = val;
  fetchCourses();
};

// 格式化日期
const formatDate = (date: string) => {
  return new Date(date).toLocaleString('zh-CN');
};

onMounted(fetchCourses);
</script>

<style scoped>
.course-management {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>