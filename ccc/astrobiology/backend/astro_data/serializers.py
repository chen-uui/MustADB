from rest_framework import serializers
from .models import MeteoriteClassification, ProteinData

class MeteoriteSerializer(serializers.ModelSerializer):
    """陨石数据序列化器"""
    
    class Meta:
        model = MeteoriteClassification
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class ProteinSerializer(serializers.ModelSerializer):
    """蛋白质数据序列化器"""
    
    class Meta:
        model = ProteinData
        fields = '__all__'
        read_only_fields = ('id', 'created_at')