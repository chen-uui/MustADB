"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# 直接导入review视图，避免路由冲突
from pdf_processor.views_review import get_pending_reviews, approve_item, reject_item

urlpatterns = [
    path('admin/', admin.site.urls),
    # 统一审核接口（直接在这里注册，避免被其他路由覆盖）
    path('api/pdf/review/pending/', get_pending_reviews, name='get_pending_reviews'),
    path('api/pdf/review/approve/', approve_item, name='approve_item'),
    path('api/pdf/review/reject/', reject_item, name='reject_item'),
    # PDF处理器路由
    path('api/pdf/', include('pdf_processor.urls')),
    path('api/direct-processing/', include('pdf_processor.urls.direct_processing_urls')),
    path('api/astro/', include('astro_data.urls')),
    path('api/meteorite/', include('meteorite_search.urls')),
]

# 在开发环境中提供媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static('/pdfs/', document_root=settings.PDF_STORAGE_PATH)
