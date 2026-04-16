from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from .models import MeteoriteClassification, ProteinData
from .serializers import MeteoriteSerializer, ProteinSerializer

logger = logging.getLogger(__name__)

class AstroDataViewSet(viewsets.ViewSet):
    """天体数据统一API视图"""
    
    @action(detail=False, methods=['get'])
    def meteorites(self, request):
        """获取陨石数据列表"""
        try:
            meteorites = MeteoriteClassification.objects.all()
            serializer = MeteoriteSerializer(meteorites, many=True)
            return Response({
                'data': serializer.data,
                'count': meteorites.count()
            })
        except Exception as e:
            logger.error(f"Error fetching meteorites: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def proteins(self, request):
        """获取蛋白质数据列表"""
        try:
            proteins = ProteinData.objects.all()
            serializer = ProteinSerializer(proteins, many=True)
            return Response({
                'data': serializer.data,
                'count': proteins.count()
            })
        except Exception as e:
            logger.error(f"Error fetching proteins: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MeteoriteViewSet(viewsets.ModelViewSet):
    """陨石数据CRUD API"""
    queryset = MeteoriteClassification.objects.all()
    serializer_class = MeteoriteSerializer
    
    def get_queryset(self):
        """支持按名称搜索"""
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        return queryset

class ProteinViewSet(viewsets.ModelViewSet):
    """蛋白质数据CRUD API"""
    queryset = ProteinData.objects.all()
    serializer_class = ProteinSerializer
    
    def get_queryset(self):
        """支持按PDB ID或蛋白质名称搜索"""
        queryset = super().get_queryset()
        pdb_id = self.request.query_params.get('pdb_id', None)
        protein_name = self.request.query_params.get('protein_name', None)
        
        if pdb_id is not None:
            queryset = queryset.filter(pdb_id__icontains=pdb_id)
        if protein_name is not None:
            queryset = queryset.filter(protein_name__icontains=protein_name)
            
        return queryset
