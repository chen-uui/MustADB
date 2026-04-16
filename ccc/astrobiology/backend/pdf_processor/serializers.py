from rest_framework import serializers

from .api_errors import get_document_processing_error
from .models import DocumentChunk, PDFDocument


class PDFDocumentSerializer(serializers.ModelSerializer):
    """PDF 文档序列化器。"""

    processing_error = serializers.SerializerMethodField()
    processing_error_code = serializers.SerializerMethodField()

    class Meta:
        model = PDFDocument
        fields = [
            "id",
            "title",
            "filename",
            "authors",
            "year",
            "journal",
            "doi",
            "file_path",
            "upload_date",
            "file_size",
            "page_count",
            "category",
            "processed",
            "sha1",
            "rag_extracted",
            "review_status",
            "review_notes",
            "reviewed_by",
            "reviewed_at",
            "uploaded_by",
            "processing_error",
            "processing_error_code",
        ]
        read_only_fields = ("id", "upload_date", "file_size", "processed", "category")

    def get_processing_error(self, obj):
        cached = get_document_processing_error(getattr(obj, "id", None))
        return cached.get("message") if cached else None

    def get_processing_error_code(self, obj):
        cached = get_document_processing_error(getattr(obj, "id", None))
        return cached.get("error_code") if cached else None


class DocumentChunkSerializer(serializers.ModelSerializer):
    """文档切块序列化器。"""

    document_title = serializers.SerializerMethodField()

    class Meta:
        model = DocumentChunk
        fields = [
            "id",
            "document",
            "document_title",
            "content",
            "page_number",
            "chunk_index",
            "embedding_id",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")

    def get_document_title(self, obj):
        if hasattr(obj, "document") and obj.document:
            return obj.document.title
        return None


class PDFUploadSerializer(serializers.Serializer):
    """PDF 上传序列化器。"""

    file = serializers.FileField()
    title = serializers.CharField(max_length=255, required=False)
    category = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)


class PDFSearchSerializer(serializers.Serializer):
    """PDF 搜索序列化器。"""

    query = serializers.CharField(max_length=1000)
    n_results = serializers.IntegerField(default=10, min_value=1, max_value=100)
    search_type = serializers.ChoiceField(choices=["semantic", "hybrid", "keyword"], default="semantic")
