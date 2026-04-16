from django.db import models
from django.utils import timezone

class MeteoriteClassification(models.Model):
    """陨石分类模型"""
    name = models.CharField(max_length=100, unique=True)
    classification = models.CharField(max_length=50)
    description = models.TextField()
    discovered_date = models.DateField(blank=True, null=True)
    mass_g = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'meteorite_classifications'
        ordering = ['name']
    
    def __str__(self) -> str:
        return str(self.name)

class ProteinData(models.Model):
    """蛋白质数据模型"""
    pdb_id = models.CharField(max_length=20, unique=True)
    uniprot_id = models.CharField(max_length=20)
    protein_name = models.CharField(max_length=200)
    organism = models.CharField(max_length=100)
    sequence_length = models.IntegerField()
    structure_method = models.CharField(max_length=50)
    resolution = models.FloatField(blank=True, null=True)
    doi = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'protein_data'
        ordering = ['pdb_id']
    
    def __str__(self) -> str:
        return f"{self.pdb_id} - {self.protein_name}"
