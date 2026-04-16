from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AstroDataViewSet, MeteoriteViewSet, ProteinViewSet

# 创建路由器并注册视图
router = DefaultRouter()
router.register(r'meteorites', MeteoriteViewSet, basename='meteorite')
router.register(r'proteins', ProteinViewSet, basename='protein')

urlpatterns = [
    path('', include(router.urls)),
    path('data/meteorites/', AstroDataViewSet.as_view({'get': 'meteorites'}), name='astro-meteorites'),
    path('data/proteins/', AstroDataViewSet.as_view({'get': 'proteins'}), name='astro-proteins'),
]