from django.contrib import admin
from .models import PDFDocument, DocumentChunk

@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'filename', 'upload_date', 'file_size', 'page_count', 'processed']
    list_filter = ['processed', 'upload_date']
    search_fields = ['title', 'filename']
    readonly_fields = ['upload_date']

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'page_number', 'chunk_index', 'created_at']
    list_filter = ['document', 'page_number']
    search_fields = ['document__title', 'content']
