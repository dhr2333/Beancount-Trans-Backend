# 标签管理系统 (Tags Management)

## 📋 概述

标签管理系统为 Beancount-Trans 提供了完整的标签管理功能，支持层级结构、启用/禁用控制等特性。

## 🗂️ 模型设计

### Tag 模型

```python
class Tag(BaseModel):
    name = models.CharField(max_length=64)          # 标签名称
    parent = models.ForeignKey('self', ...)         # 父标签（支持层级）
    description = models.TextField(blank=True)      # 标签描述
    owner = models.ForeignKey(User, ...)            # 所属用户
    enable = models.BooleanField(default=True)      # 是否启用
```

**核心方法：**
- `get_full_path()` - 获取完整路径，如 "Category/EDUCATION"
- `has_children()` - 检查是否有子标签
- `get_all_children()` - 递归获取所有子标签ID
- `delete_with_children(force)` - 删除标签及其子标签

## 🔌 API 接口

### 基础路由
```
/api/tags/
```

### 接口列表

#### 1. 标签列表（支持过滤）
```http
GET /api/tags/
```

**查询参数：**
- `name` - 标签名称（模糊匹配）
- `enable` - 是否启用（true/false）
- `is_root` - 是否为根标签（true/false）
- `parent` - 父标签ID
- `parent__name` - 父标签名称（模糊匹配）

**示例：**
```bash
# 获取所有启用的标签
GET /api/tags/?enable=true

# 获取所有根标签
GET /api/tags/?is_root=true

# 搜索名称包含"Category"的标签
GET /api/tags/?name=Category
```

**响应：**
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "name": "Category",
      "parent": null,
      "parent_name": null,
      "full_path": "Category",
      "description": "分类标签",
      "enable": true,
      "has_children": true,
      "created": "2025-04-08T10:00:00Z",
      "modified": "2025-04-08T10:00:00Z"
    }
  ]
}
```

#### 2. 树形结构展示
```http
GET /api/tags/tree/
```

返回所有根标签及其递归的子标签树形结构。

**响应：**
```json
[
  {
    "id": 1,
    "name": "Category",
    "full_path": "Category",
    "enable": true,
    "children": [
      {
        "id": 2,
        "name": "EDUCATION",
        "full_path": "Category/EDUCATION",
        "enable": true,
        "children": []
      },
      {
        "id": 3,
        "name": "ENTERTAINMENT",
        "full_path": "Category/ENTERTAINMENT",
        "enable": true,
        "children": []
      }
    ]
  }
]
```

#### 3. 创建标签
```http
POST /api/tags/
```

**请求体：**
```json
{
  "name": "EDUCATION",
  "parent": 1,  // 可选，父标签ID
  "description": "教育相关支出",
  "enable": true
}
```

**响应：**
```json
{
  "id": 2,
  "name": "EDUCATION",
  "parent": 1,
  "parent_name": "Category",
  "full_path": "Category/EDUCATION",
  "description": "教育相关支出",
  "enable": true,
  "has_children": false,
  "created": "2025-04-08T10:00:00Z",
  "modified": "2025-04-08T10:00:00Z"
}
```

#### 4. 更新标签
```http
PUT /api/tags/{id}/
PATCH /api/tags/{id}/
```

**请求体（PATCH，部分更新）：**
```json
{
  "description": "更新后的描述"
}
```

#### 5. 删除标签
```http
DELETE /api/tags/{id}/
```

**请求体（可选）：**
```json
{
  "force": false  // 是否强制删除（包括子标签）
}
```

**响应：**
```json
{
  "message": "标签删除成功",
  "result": {
    "deleted_tag": {
      "id": 2,
      "name": "EDUCATION",
      "full_path": "Category/EDUCATION"
    },
    "deleted_children_count": 0,
    "affected_mappings": 0
  }
}
```

#### 6. 获取子标签
```http
GET /api/tags/{id}/children/
```

返回指定标签的直接子标签列表。

#### 7. 获取所有后代标签
```http
GET /api/tags/{id}/descendants/
```

**响应：**
```json
{
  "tag_id": 1,
  "tag_name": "Category",
  "descendant_ids": [2, 3, 4, 5],
  "count": 4
}
```

#### 8. 切换启用状态
```http
POST /api/tags/{id}/toggle_enable/
```

快速切换标签的启用/禁用状态。禁用父标签会自动禁用所有子标签。

**响应：**
```json
{
  "message": "标签已禁用",
  "tag": {
    "id": 1,
    "name": "Category",
    "enable": false
  }
}
```

#### 9. 批量操作
```http
POST /api/tags/batch_update/
```

**请求体：**
```json
{
  "tag_ids": [1, 2, 3],
  "action": "disable"  // "enable" | "disable" | "delete"
}
```

**响应：**
```json
{
  "message": "批量操作成功",
  "result": {
    "action": "disable",
    "affected_count": 5,
    "tag_ids": [1, 2, 3, 4, 5]  // 包括子标签
  }
}
```

#### 10. 统计信息
```http
GET /api/tags/stats/
```

**响应：**
```json
{
  "total": 10,
  "enabled": 8,
  "disabled": 2,
  "root_tags": 3,
  "child_tags": 7
}
```

## 🔐 权限控制

- **认证用户**：可以管理自己的标签（增删改查）
- **匿名用户**：只能查看 ID=1 用户的标签（只读）
- **管理员**：可以管理所有用户的标签

## 📝 使用示例

### 创建层级标签结构

```python
# 1. 创建根标签
POST /api/tags/
{
  "name": "Category",
  "description": "分类标签根节点"
}
# 返回 id: 1

# 2. 创建子标签
POST /api/tags/
{
  "name": "EDUCATION",
  "parent": 1,
  "description": "教育支出"
}
# 返回 id: 2, full_path: "Category/EDUCATION"

# 3. 创建孙标签
POST /api/tags/
{
  "name": "Books",
  "parent": 2,
  "description": "购买图书"
}
# 返回 id: 3, full_path: "Category/EDUCATION/Books"
```

### 查询和过滤

```bash
# 获取所有启用的根标签
GET /api/tags/?enable=true&is_root=true

# 搜索名称包含"EDUCATION"的标签
GET /api/tags/?name=EDUCATION

# 获取指定父标签下的所有子标签
GET /api/tags/?parent=1
```

### 树形展示

```bash
# 获取完整的标签树
GET /api/tags/tree/
```

### 批量管理

```bash
# 批量禁用多个标签（会自动禁用子标签）
POST /api/tags/batch_update/
{
  "tag_ids": [1, 2, 3],
  "action": "disable"
}

# 批量删除
POST /api/tags/batch_update/
{
  "tag_ids": [4, 5],
  "action": "delete"
}
```

## ⚠️ 注意事项

1. **标签名称限制**：不能包含空格、#号、换行符等特殊字符
2. **父标签状态**：禁用父标签会自动禁用所有子标签
3. **删除保护**：有子标签的标签需要使用 `force=true` 才能删除
4. **循环引用**：系统会自动检测并阻止循环引用
5. **唯一性**：同一用户下，标签名称必须唯一

## 🚀 下一步：集成到映射系统

Phase 2 将实现：
1. 在 Expense/Assets/Income 模型中添加 `tags` 多对多字段
2. 在映射管理界面中支持标签选择
3. 在交易解析时自动应用映射的标签

## 📊 数据库表结构

**表名：** `tags_tag`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger | 主键 |
| name | VARCHAR(64) | 标签名称 |
| description | TEXT | 标签描述 |
| enable | Boolean | 是否启用 |
| parent_id | BigInteger | 父标签ID（外键） |
| owner_id | BigInteger | 所属用户ID（外键） |
| created | DateTime | 创建时间 |
| modified | DateTime | 修改时间 |

**索引：**
- PRIMARY KEY (id)
- UNIQUE (name, owner_id)
- INDEX (owner_id)
- INDEX (parent_id)

## 🔧 Admin 管理

标签可以在 Django Admin 后台中管理（需要注册到 admin.py）：

```python
# project/apps/tags/admin.py
from django.contrib import admin
from project.apps.tags.models import Tag

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'full_path', 'owner', 'enable', 'created']
    list_filter = ['enable', 'created']
    search_fields = ['name', 'description']
    ordering = ['name']
```

## ✅ 功能清单

- [x] Tag 模型设计
- [x] 层级结构支持
- [x] 完整的 CRUD API
- [x] 树形展示接口
- [x] 启用/禁用控制
- [x] 批量操作
- [x] 过滤和搜索
- [x] 权限控制
- [x] 数据库迁移
- [ ] 与映射系统集成（Phase 2）
- [ ] 标签统计分析（Phase 3）

