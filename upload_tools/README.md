# ShareUSTC 批量上传工具

> 命令行工具，用于批量上传学习资料到 ShareUSTC 平台

---

## 快速开始

### 1. 安装

```bash
# 使用 pip 安装（推荐，发布后可用）
pip install shareustc-upload

# 或从源码安装
git clone <repository>
cd upload_tools
pip install -r requirements.txt
pip install -e .
```

Ubuntu 用户请参考 [INSTALL_UBUNTU.md](./INSTALL_UBUNTU.md) 获取详细安装指南。

---

### 2. 初始化配置

```bash
# 生成示例配置文件和 CSV 模板
shareustc-upload --template

# 你会看到以下输出：
# ✓ 已生成示例文件:
#   - 配置文件示例: config.example.yaml
#   - CSV 示例: my_upload.example.csv
```

### 3. 配置服务器地址

```bash
# 复制示例配置文件
cp config.example.yaml config.yaml

# 编辑配置文件，设置服务器地址
nano config.yaml

# 修改 server.base_url:
server:
  base_url: "https://share.ustcer.top"  # 修改为你的服务器地址
```

配置文件支持放在以下位置：
- 当前目录的 `config.yaml`（推荐）
- 用户目录的 `~/.shareustc/config.yaml`

### 4. 测试登录

```bash
# 测试登录（不需要 CSV 文件）
shareustc-upload --login

# 输入用户名和密码
# 登录成功后会保存 Cookie，下次无需重复登录
```

---

## 准备 CSV 文件

参考生成的 `my_upload.example.csv` 创建你的上传列表文件。

### CSV 格式说明

**必需字段:**

| 字段 | 说明 | 示例 |
|------|------|------|
| title | 资源标题 | "2025年线性代数期中试卷" |
| category | 资源分类 | past_paper/note/review_outline |
| file_path | 本地文件路径 | "/path/to/file.pdf" |

**可选字段:**

| 字段 | 说明 | 示例 |
|------|------|------|
| course_name | 适用课程（自由文本） | "线性代数" |
| related_courses | 关联课程（分号分隔） | "线性代数I;线性代数II" |
| related_teachers | 关联教师（分号分隔） | "张三;李四" |
| tags | 标签（分号分隔） | "期中;2025;试卷" |
| description | 资源描述 | "个人整理的复习资料" |

### 完整示例

```csv
title,course_name,related_courses,related_teachers,category,tags,description,file_path
2025年线性代数期中试卷,线性代数,线性代数I;线性代数II,张三;李四,past_paper,期中;2025;试卷,2025年春季学期期中考试试卷,/path/to/exam1.pdf
微积分复习笔记,微积分,微积分上;微积分下,王五,note,复习;笔记;总结,第一章到第五章重点,/path/to/notes.md
```

### 资源分类选项

- `exam_result` - 考试成绩分布
- `learning_note` - 学习心得
- `past_paper` - 往年试卷
- `note` - 笔记
- `review_outline` - 复习提纲
- `lecture` - 讲义
- `other` - 其他

---

## 交互式课程/教师匹配

当 CSV 中填写的课程或教师名称与系统中不完全相同时，工具会：

1. **首先尝试精确匹配**（完全相等）
2. **如果失败，显示相似度前5的候选项**
3. **要求用户输入编号选择**（1-5 选择，0 跳过）

**示例交互：**
```
⚠ 未找到精确匹配的课程: "线代"
ℹ 请选择最相似的课程（输入编号），或输入 0 跳过:

  [1] 线性代数
      相似度: 66.67% ██████▓░░░░░

  [2] 线性代数与解析几何
      相似度: 40.00% ████░░░░░░░░

  [0] 跳过此课程（不关联）

请选择 [0-5]: 1
✓ 已选择: 线性代数 (SN: 1)
```

**非交互式模式：**
```bash
# 在脚本或自动化场景下使用，跳过交互选择
shareustc-upload --csv my_upload.csv --non-interactive
```

---

## 命令行参数

```
Usage: shareustc-upload [OPTIONS]

Options:
  --csv PATH              CSV 文件路径（包含要上传的资源列表）
  --config PATH           配置文件路径（默认使用当前目录或用户目录的 config.yaml）
  --login                 仅执行登录操作（测试认证）
  --logout                登出并清除登录状态
  --template              在当前目录生成示例配置文件和 CSV 模板
  --resume                从上次中断处继续上传
  --dry-run               模拟运行，验证 CSV 格式和文件路径，不上传实际文件
  --non-interactive       非交互式模式（模糊匹配时自动跳过）
  --output PATH           报告输出目录（默认当前目录）
  --format [csv|html|both] 报告格式
  --verbose               显示详细日志（DEBUG 级别）
  --version               显示版本信息
  --help                  显示帮助信息
```

---

## 使用示例

### 示例 1: 完整使用流程

```bash
# 1. 生成示例文件
shareustc-upload --template

# 2. 配置服务器
cp config.example.yaml config.yaml
# 编辑 config.yaml 设置服务器地址

# 3. 测试登录
shareustc-upload --login

# 4. 准备 CSV
cp my_upload.example.csv my_upload.csv
# 编辑 my_upload.csv 填写你的资源

# 5. 验证配置（模拟运行）
shareustc-upload --csv my_upload.csv --dry-run

# 6. 执行上传
shareustc-upload --csv my_upload.csv
```

### 示例 2: 仅登录测试

```bash
shareustc-upload --login
```

### 示例 3: 断点续传

```bash
# 上次上传中断后
shareustc-upload --csv my_upload.csv --resume
```

### 示例 4: 生成 HTML 报告

```bash
shareustc-upload --csv my_upload.csv --format html --output ./reports
```

### 示例 5: 模拟运行（测试 CSV 格式）

```bash
shareustc-upload --csv my_upload.csv --dry-run
```

### 示例 6: 使用指定配置文件

```bash
shareustc-upload --csv my_upload.csv --config /path/to/config.yaml
```

---

## 配置文件说明

工具会按以下顺序查找配置文件：

1. `--config` 参数指定的文件
2. 当前目录的 `config.yaml`
3. 用户目录的 `~/.shareustc/config.yaml`

**必需配置项:**

```yaml
server:
  base_url: "https://share.ustcer.top"  # 你的服务器地址
```

**完整配置示例:**

```yaml
server:
  base_url: "https://share.ustcer.top"
  timeout: 300
  retry_count: 3

upload:
  max_file_size: 104857600  # 100MB

output:
  report_format: "csv"
  verbose: true
```

---

## 常见问题

### Q: 如何生成示例文件？

```bash
shareustc-upload --template
```

这会生成 `config.example.yaml` 和 `my_upload.example.csv` 两个示例文件。

### Q: 如何测试登录？

```bash
shareustc-upload --login
```

不需要指定 CSV 文件，单独测试登录功能。

### Q: 未找到配置文件？

**错误信息:**
```
✗ 错误: 服务器地址未配置
  请编辑 config.yaml 设置服务器地址:
  server:
    base_url: "https://share.ustcer.top"
```

**解决方案:**

```bash
# 1. 生成示例文件
shareustc-upload --template

# 2. 复制并编辑
cp config.example.yaml config.yaml
nano config.yaml
```

### Q: 上传失败如何重试？

工具会自动重试 3 次。如果仍然失败，使用 `--resume` 参数从中断处继续：

```bash
shareustc-upload --csv my_upload.csv --resume
```

### Q: 课程/教师名称不完全匹配怎么办？

工具使用**交互式模糊匹配**：

1. **首先尝试精确匹配**（完全相等）
2. **如果失败，显示相似度前5的候选项**
3. **用户输入编号 1-5 选择，或 0 跳过**

如果不想交互，使用 `--non-interactive` 参数：
```bash
shareustc-upload --csv my_upload.csv --non-interactive
```

详细匹配原理请参考 [FUZZY_MATCHING.md](./FUZZY_MATCHING.md)。

### Q: 如何查看上传结果？

上传完成后会生成报告文件：
- CSV 报告：`upload_report_YYYYMMDD_HHMMSS.csv`
- HTML 报告（如果指定 `--format html`）

报告包含：
- 上传状态（成功/失败）
- 资源ID（成功时）
- 错误信息（失败时）

### Q: Cookie 保存在哪里？

默认保存在当前目录的 `.shareustc/cookies.json`，文件权限设置为仅当前用户可读（600）。

### Q: 大文件上传失败怎么办？

工具支持大文件流式上传。如果遇到大文件上传失败：

1. **检查网络连接**：确保网络稳定，上传过程中不要断网
2. **增加超时时间**：在 `config.yaml` 中增加 `server.timeout` 配置
   ```yaml
   server:
     base_url: "https://share.ustcer.top"
     timeout: 600  # 增加到10分钟（默认5分钟）
   ```
3. **查看进度**：大文件（>10MB）上传时会显示进度条，可以看到上传进度
4. **测试功能**：使用测试脚本验证大文件上传功能
   ```bash
   # 创建50MB测试文件并上传
   python tests/test_large_upload.py --config config.yaml --size 50
   ```

工具会自动检测文件大小：
- **小文件**（<10MB）：普通上传
- **大文件**（≥10MB）：流式上传，显示进度条，自动调整超时时间

### Q: 支持哪些文件类型？

支持的文件类型：
- 文档：pdf, doc, docx, ppt, pptx, txt, md
- 图片：jpg, jpeg, png
- 压缩包：zip

---

---

## 大文件上传

工具对大文件（≥10MB）上传进行了优化：

### 自动检测
- 小文件（<10MB）：使用标准上传方式
- 大文件（≥10MB）：
  - 使用**流式上传**减少内存占用
  - 显示**进度条**实时反馈上传进度
  - 自动计算并调整超时时间

### 配置超时

对于特别大的文件或较慢的网络，建议增加超时时间：

```yaml
# config.yaml
server:
  base_url: "https://share.ustcer.top"
  timeout: 600  # 10分钟，根据文件大小和网络速度调整
```

### 测试大文件上传

```bash
# 使用测试脚本验证功能（创建50MB测试文件并上传）
python tests/test_large_upload.py --config config.yaml --size 50

# 测试完成后自动清理测试文件
python tests/test_large_upload.py --config config.yaml --size 50 --cleanup
```

---

## 文档索引

- [PRD.md](./PRD.md) - 产品需求文档
- [techspec.md](./techspec.md) - 技术规格文档
- [INSTALL_UBUNTU.md](./INSTALL_UBUNTU.md) - Ubuntu 安装指南
- [dev_status.md](./dev_status.md) - 开发进度文档

---

## 支持与反馈

如有问题或建议，请通过以下方式反馈：
- 在 GitHub 提交 Issue
- 联系平台管理员
- 使用 `--verbose` 参数获取详细日志进行调试
