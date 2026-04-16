"""
统一审核视图
合并PDF审核和陨石审核
"""
import logging
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import PDFDocument

# 导入陨石审核相关
try:
    from meteorite_search.review_models import PendingMeteorite
    from meteorite_search.review_system_v2 import NewReviewSystem, new_review_system
    METEORITE_REVIEW_AVAILABLE = True
except ImportError:
    METEORITE_REVIEW_AVAILABLE = False
    PendingMeteorite = None
    new_review_system = None

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_reviews(request):
    """
    获取所有待审核项目（PDF和陨石）
    
    GET /api/pdf/review/pending/
    Query params:
    - type: 'pdf' | 'meteorite' | 'all' (default: 'all')
    - status: 'pending' | 'under_review' | 'needs_revision' (default: 'pending')
    - page: 页码
    - page_size: 每页数量
    """
    try:
        # request.user 已经通过认证中间件设置
        logger.info(f"Review request from user: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
        review_type = request.GET.get('type', 'all')  # pdf, meteorite, all
        review_status = request.GET.get('status', 'pending')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        results = {
            'pdfs': [],
            'meteorites': [],
            'total': 0,
            'page': page,
            'page_size': page_size
        }
        
        # 获取待审核的PDF
        if review_type in ['pdf', 'all']:
            # 优化查询：使用select_related预加载外键，避免N+1查询
            # 使用only()只选择需要的字段，减少数据传输
            pdf_queryset = PDFDocument._default_manager.filter(
                review_status=review_status
            ).select_related(
                'uploaded_by', 'reviewed_by'
            ).only(
                'id', 'title', 'filename', 'authors', 'year', 'journal',
                'file_size', 'page_count', 'upload_date', 'review_status',
                'review_notes', 'uploaded_by', 'reviewed_by'
            ).order_by('-upload_date')
            
            # 计算PDF总数（用于分页）
            pdf_total = pdf_queryset.count()
            
            # 分页：如果type='all'，需要分别计算PDF和陨石的分页
            if review_type == 'all':
                # 合并分页：先取PDF，再取陨石，确保总数正确
                pdf_page_size = page_size // 2 if review_type == 'all' else page_size
                start = (page - 1) * pdf_page_size
                end = start + pdf_page_size
            else:
                # 只查询PDF时，使用完整分页
                start = (page - 1) * page_size
                end = start + page_size
            
            pdfs = pdf_queryset[start:end]
            results['pdfs'] = [{
                'id': str(pdf.id),
                'type': 'pdf',
                'title': pdf.title,
                'filename': pdf.filename,
                'authors': pdf.authors,
                'year': pdf.year,
                'journal': pdf.journal,
                'file_size': pdf.file_size,
                'page_count': pdf.page_count,
                'upload_date': pdf.upload_date.isoformat(),
                'uploaded_by': pdf.uploaded_by.username if pdf.uploaded_by else None,
                'review_status': pdf.review_status,
                'review_notes': pdf.review_notes
            } for pdf in pdfs]
            results['pdf_total'] = pdf_total
        
        # 获取待审核的陨石
        if review_type in ['meteorite', 'all'] and METEORITE_REVIEW_AVAILABLE and new_review_system:
            try:
                meteorites = new_review_system.get_pending_reviews(status=review_status)
                
                # 计算陨石总数
                meteorite_total = len(meteorites) if isinstance(meteorites, list) else 0
                
                # 分页：如果type='all'，需要分别计算PDF和陨石的分页
                if review_type == 'all':
                    # 合并分页：先取PDF，再取陨石
                    meteorite_page_size = page_size // 2
                    start = (page - 1) * meteorite_page_size
                    end = start + meteorite_page_size
                else:
                    # 只查询陨石时，使用完整分页
                    start = (page - 1) * page_size
                    end = start + page_size
                
                # 确保meteorites是列表
                if not isinstance(meteorites, list):
                    meteorites = list(meteorites) if meteorites else []
                
                results['meteorites'] = [{
                    'id': str(meteorite['id']),
                    'type': 'meteorite',
                    'name': meteorite.get('name', 'Unknown'),
                    'classification': meteorite.get('classification', ''),
                    'discovery_location': meteorite.get('discovery_location', ''),
                    'origin': meteorite.get('origin', ''),
                    'confidence_score': meteorite.get('confidence_score', 0),
                    'created_at': meteorite.get('created_at', ''),
                    'review_status': meteorite.get('review_status', 'pending'),
                    'priority': meteorite.get('priority', 1),
                    'assigned_reviewer': meteorite.get('assigned_reviewer'),
                    'organic_compounds_summary': meteorite.get('organic_compounds_summary', ''),
                    'references_count': meteorite.get('references_count', 0)
                } for meteorite in meteorites[start:end]]
                results['meteorite_total'] = meteorite_total
            except Exception as e:
                logger.error(f"Error fetching meteorite reviews: {str(e)}")
                results['meteorites'] = []
                results['meteorite_total'] = 0
        
        # 计算总数：PDF总数 + 陨石总数
        pdf_total = results.get('pdf_total', len(results['pdfs']))
        meteorite_total = results.get('meteorite_total', len(results['meteorites']))
        results['total'] = pdf_total + meteorite_total
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting pending reviews: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _approve_pdf(pdf_id, reviewer, notes):
    """审核通过PDF的内部函数"""
    pdf = PDFDocument._default_manager.select_for_update().get(id=pdf_id)
    pdf.review_status = 'approved'
    pdf.review_notes = notes
    pdf.reviewed_by = reviewer
    pdf.reviewed_at = timezone.now()
    pdf.save(update_fields=['review_status', 'review_notes', 'reviewed_by', 'reviewed_at'])
    return {'success': True, 'message': 'PDF approved successfully'}


# 创建包装函数以解决Pyright类型检查问题
from typing import Dict, Any, cast

def approve_meteorite_wrapper(pending_id: int, reviewer, notes: str = "") -> Dict[str, Any]:
    """包装approve_meteorite方法以解决Pyright类型检查问题"""
    if new_review_system is not None:
        # 使用getattr安全访问方法
        method = getattr(new_review_system, 'approve_meteorite')
        result = method(pending_id=pending_id, reviewer=reviewer, notes=notes)
        return cast(Dict[str, Any], result)
    return {'success': False, 'error': 'Meteorite review system not available'}

def reject_meteorite_wrapper(pending_id: int, reviewer, reason: str, category: str = 'data_quality', notes: str = "") -> Dict[str, Any]:
    """包装reject_meteorite方法以解决Pyright类型检查问题"""
    if new_review_system is not None:
        # 使用getattr安全访问方法
        method = getattr(new_review_system, 'reject_meteorite')
        result = method(pending_id=pending_id, reviewer=reviewer, reason=reason, category=category, notes=notes)
        return cast(Dict[str, Any], result)
    return {'success': False, 'error': 'Meteorite review system not available'}


def _approve_meteorite(meteorite_id, reviewer, notes):
    """审核通过陨石的内部函数"""
    if not METEORITE_REVIEW_AVAILABLE or not new_review_system:
        return {'success': False, 'error': 'Meteorite review system not available'}
    
    # 使用包装函数调用方法以解决Pyright类型检查问题
    result = approve_meteorite_wrapper(
        pending_id=int(meteorite_id),
        reviewer=reviewer,
        notes=notes
    )
    return result


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def approve_item(request):
    """
    审核通过项目（PDF或陨石）
    
    POST /api/review/approve/
    Body:
    {
        "type": "pdf" | "meteorite",
        "id": "item_id",
        "notes": "审核备注"
    }
    """
    try:
        item_type = request.data.get('type')
        item_id = request.data.get('id')
        notes = request.data.get('notes', '')
        
        if not item_type or not item_id:
            return Response({
                'error': 'Missing type or id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if item_type == 'pdf':
            try:
                result = _approve_pdf(item_id, request.user, notes)
                return Response(result, status=status.HTTP_200_OK)
            except PDFDocument._default_manager.model.DoesNotExist:
                return Response({
                    'error': 'PDF not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        elif item_type == 'meteorite':
            try:
                result = _approve_meteorite(item_id, request.user, notes)
                if isinstance(result, dict) and result.get('success'):
                    return Response({
                        'success': True,
                        'message': 'Meteorite approved successfully'
                    }, status=status.HTTP_200_OK)
                else:
                    error_msg = result.get('error', 'Approval failed') if isinstance(result, dict) else 'Approval failed'
                    return Response({
                        'error': error_msg
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error approving meteorite: {str(e)}", exc_info=True)
                return Response({
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            return Response({
                'error': 'Invalid type or type not available'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error approving item: {str(e)}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _reject_pdf(pdf_id, reviewer, notes):
    """审核拒绝PDF的内部函数"""
    pdf = PDFDocument._default_manager.select_for_update().get(id=pdf_id)
    pdf.review_status = 'rejected'
    pdf.review_notes = notes
    pdf.reviewed_by = reviewer
    pdf.reviewed_at = timezone.now()
    pdf.save(update_fields=['review_status', 'review_notes', 'reviewed_by', 'reviewed_at'])
    return {'success': True, 'message': 'PDF rejected'}


def _reject_meteorite(meteorite_id, reviewer, notes):
    """审核拒绝陨石的内部函数"""
    if not METEORITE_REVIEW_AVAILABLE or not new_review_system:
        return {'success': False, 'error': 'Meteorite review system not available'}
    
    # 使用包装函数调用方法以解决Pyright类型检查问题
    result = reject_meteorite_wrapper(
        pending_id=int(meteorite_id),
        reviewer=reviewer,
        reason=notes or 'Rejected by reviewer',
        category='data_quality',
        notes=notes
    )
    return result


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def reject_item(request):
    """
    审核拒绝项目（PDF或陨石）
    
    POST /api/review/reject/
    Body:
    {
        "type": "pdf" | "meteorite",
        "id": "item_id",
        "notes": "拒绝原因"
    }
    """
    try:
        item_type = request.data.get('type')
        item_id = request.data.get('id')
        notes = request.data.get('notes', '')
        
        if not item_type or not item_id:
            return Response({
                'error': 'Missing type or id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if item_type == 'pdf':
            try:
                result = _reject_pdf(item_id, request.user, notes)
                return Response(result, status=status.HTTP_200_OK)
            except PDFDocument._default_manager.model.DoesNotExist:
                return Response({
                    'error': 'PDF not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        elif item_type == 'meteorite':
            try:
                result = _reject_meteorite(item_id, request.user, notes)
                if isinstance(result, dict) and result.get('success'):
                    return Response({
                        'success': True,
                        'message': 'Meteorite rejected'
                    }, status=status.HTTP_200_OK)
                else:
                    error_msg = result.get('error', 'Rejection failed') if isinstance(result, dict) else 'Rejection failed'
                    return Response({
                        'error': error_msg
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error rejecting meteorite: {str(e)}", exc_info=True)
                return Response({
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            return Response({
                'error': 'Invalid type or type not available'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error rejecting item: {str(e)}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

