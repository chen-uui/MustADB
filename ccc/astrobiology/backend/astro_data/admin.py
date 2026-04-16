from django.contrib import admin
from .models import MeteoriteClassification, ProteinData

@admin.register(MeteoriteClassification)
class MeteoriteClassificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'classification', 'discovered_date', 'mass_g']
    list_filter = ['classification', 'discovered_date']
    search_fields = ['name', 'description']

@admin.register(ProteinData)
class ProteinDataAdmin(admin.ModelAdmin):
    list_display = ['pdb_id', 'protein_name', 'organism', 'sequence_length', 'structure_method']
    list_filter = ['organism', 'structure_method']
    search_fields = ['pdb_id', 'protein_name', 'uniprot_id']
