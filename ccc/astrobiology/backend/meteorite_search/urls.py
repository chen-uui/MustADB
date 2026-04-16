from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'meteorite_search'

# 创建DRF路由器
router = DefaultRouter()
router.register(r'meteorites', views.MeteoriteViewSet, basename='meteorite')

urlpatterns = [
    # DRF ViewSet路由 - 直接包含在根路径下
    path('', include(router.urls)),
    
    # 新的三层数据流转API (v2)
    path('v2/', include('meteorite_search.review_urls')),
]