"""
新的陨石数据审核URL配置
支持三层数据流转的API路由
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import review_views

# 创建路由器
router = DefaultRouter()

# 注册ViewSet
router.register(r'pending', review_views.PendingMeteoriteViewSet, basename='pending-meteorite')
router.register(r'approved', review_views.ApprovedMeteoriteViewSet, basename='approved-meteorite')
router.register(r'rejected', review_views.RejectedMeteoriteViewSet, basename='rejected-meteorite')

# URL模式
urlpatterns = [
    # ViewSet路由
    path('', include(router.urls)),
    
    # 传统API路由
    path('submit/', review_views.submit_meteorite_data, name='submit-meteorite-data'),
    path('review-queue/', review_views.get_review_queue, name='get-review-queue'),
    path('recycle-bin/', review_views.get_recycle_bin, name='get-recycle-bin'),
    path('statistics/', review_views.get_review_statistics, name='get-review-statistics'),
    # path('options/', views_new.get_meteorite_options, name='get-meteorite-options'),  # 已移除，统一使用MeteoriteViewSet的options action
]

"""
API端点说明：

1. 待审核陨石 (PendingMeteorite)
   - GET /api/v2/pending/ - 获取待审核列表
   - POST /api/v2/pending/ - 创建待审核数据
   - GET /api/v2/pending/{id}/ - 获取单个待审核数据
   - PUT /api/v2/pending/{id}/ - 更新待审核数据
   - DELETE /api/v2/pending/{id}/ - 删除待审核数据
   - POST /api/v2/pending/{id}/assign_reviewer/ - 分配审核人员
   - POST /api/v2/pending/{id}/approve/ - 批准数据
   - POST /api/v2/pending/{id}/reject/ - 拒绝数据
   - POST /api/v2/pending/{id}/request_revision/ - 要求修订

2. 已批准陨石 (ApprovedMeteorite)
   - GET /api/v2/approved/ - 获取已批准列表
   - GET /api/v2/approved/{id}/ - 获取单个已批准数据
   - GET /api/v2/approved/statistics/ - 获取统计信息

3. 回收站陨石 (RejectedMeteorite)
   - GET /api/v2/rejected/ - 获取回收站列表
   - GET /api/v2/rejected/{id}/ - 获取单个回收站数据
   - POST /api/v2/rejected/{id}/restore/ - 恢复数据
   - DELETE /api/v2/rejected/{id}/permanent_delete/ - 永久删除

4. 其他API
   - POST /api/v2/submit/ - 提交陨石数据
   - GET /api/v2/review-queue/ - 获取审核队列
   - GET /api/v2/recycle-bin/ - 获取回收站数据
   - GET /api/v2/statistics/ - 获取审核统计
   - GET /api/v2/options/ - 获取选项数据

查询参数示例：
- 过滤: ?review_status=pending&classification=Chondrite
- 搜索: ?search=Mars
- 排序: ?ordering=-created_at
- 分页: ?page=1&page_size=20
"""