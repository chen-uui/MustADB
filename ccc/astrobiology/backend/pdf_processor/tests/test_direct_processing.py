"""
直接处理模块的单元测试
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from ..direct_processing.document_processor import DirectDocumentProcessor
from ..direct_processing.llm_analyzer import LLMAnalyzer
from ..direct_processing.data_extractor import DataExtractor
from ..direct_processing.result_validator import ResultValidator
from ..direct_processing.utils import extract_pdf_text, validate_pdf_file
from ..models.direct_processing_models import DirectProcessingResult, ProcessingTask


class TestDirectDocumentProcessor(TestCase):
    """测试直接文档处理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.processor = DirectDocumentProcessor()
        
    def test_processor_initialization(self):
        """测试处理器初始化"""
        self.assertIsNotNone(self.processor.llm_analyzer)
        self.assertIsNotNone(self.processor.data_extractor)
        self.assertIsNotNone(self.processor.validator)
    
    @patch('pdf_processor.direct_processing.document_processor.extract_pdf_text')
    @patch('pdf_processor.direct_processing.document_processor.LLMAnalyzer')
    @patch('pdf_processor.direct_processing.document_processor.DataExtractor')
    @patch('pdf_processor.direct_processing.document_processor.ResultValidator')
    def test_process_document_success(self, mock_validator, mock_extractor, mock_analyzer, mock_extract_text):
        """测试文档处理成功"""
        # 模拟依赖
        mock_extract_text.return_value = "Sample PDF text content"
        
        mock_analysis_result = Mock()
        mock_analysis_result.structured_data = {"test": "data"}
        
        mock_extracted_data = Mock()
        mock_validated_result = Mock()
        mock_validated_result.validation_checks = []
        mock_validated_result.data = mock_extracted_data
        
        mock_analyzer.return_value.analyze_document.return_value = mock_analysis_result
        mock_extractor.return_value.extract_structured_data.return_value = mock_extracted_data
        mock_validator.return_value.validate_result.return_value = mock_validated_result
        
        # 执行测试
        result = self.processor.process_document("test.pdf")
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.document_path, "test.pdf")
        self.assertGreater(result.processing_time, 0)
    
    def test_process_document_file_not_found(self):
        """测试文件不存在的情况"""
        with self.assertRaises(Exception):
            self.processor.process_document("nonexistent.pdf")
    
    @patch('pdf_processor.direct_processing.document_processor.extract_pdf_text')
    def test_process_document_empty_text(self, mock_extract_text):
        """测试空文本的情况"""
        mock_extract_text.return_value = ""
        
        with self.assertRaises(ValueError):
            self.processor.process_document("test.pdf")


class TestLLMAnalyzer(TestCase):
    """测试LLM分析器"""
    
    def setUp(self):
        """设置测试环境"""
        self.analyzer = LLMAnalyzer()
    
    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        self.assertIsNotNone(self.analyzer.llm_client)
        self.assertIsNotNone(self.analyzer.prompt_templates)
    
    @patch('pdf_processor.direct_processing.llm_analyzer.requests.post')
    def test_analyze_document_success(self, mock_post):
        """测试文档分析成功"""
        # 模拟LLM响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': '{"meteorite_data": {"name": "Test Meteorite"}}'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # 执行测试
        result = self.analyzer.analyze_document("Test text content")
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.structured_data)
    
    def test_analyze_document_long_text(self):
        """测试长文本处理"""
        long_text = "x" * 150000  # 超过10万字符
        
        with patch('pdf_processor.direct_processing.llm_analyzer.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {'response': '{"test": "data"}'}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            result = self.analyzer.analyze_document(long_text)
            
            # 验证文本被截断
            self.assertIsNotNone(result)
    
    def test_parse_llm_response_json(self):
        """测试JSON响应解析"""
        json_response = '{"meteorite_data": {"name": "Test Meteorite"}}'
        result = self.analyzer._parse_llm_response(json_response)
        
        self.assertIsInstance(result, dict)
        self.assertIn('meteorite_data', result)
    
    def test_parse_llm_response_text(self):
        """测试文本响应解析"""
        text_response = "陨石名称: Test Meteorite\n分类: Chondrite"
        result = self.analyzer._parse_llm_response(text_response)
        
        self.assertIsInstance(result, dict)


class TestDataExtractor(TestCase):
    """测试数据提取器"""
    
    def setUp(self):
        """设置测试环境"""
        self.extractor = DataExtractor()
    
    def test_extractor_initialization(self):
        """测试提取器初始化"""
        self.assertIsNotNone(self.extractor)
    
    def test_extract_meteorite_data(self):
        """测试陨石数据提取"""
        raw_data = {
            'meteorite_data': {
                'name': 'Test Meteorite',
                'classification': 'Chondrite'
            }
        }
        
        result = self.extractor.extract_meteorite_data(raw_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('name', result)
        self.assertIn('classification', result)
    
    def test_extract_organic_compounds(self):
        """测试有机化合物提取"""
        raw_data = {
            'organic_compounds': {
                'compounds': 'amino acids, proteins',
                'concentration': '10 ppm'
            }
        }
        
        result = self.extractor.extract_organic_compounds(raw_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('compounds', result)
        self.assertIn('concentration', result)
    
    def test_extract_mineral_relationships(self):
        """测试矿物关系提取"""
        raw_data = {
            'mineral_relationships': {
                'minerals': 'olivine, pyroxene',
                'relationships': 'crystallization sequence'
            }
        }
        
        result = self.extractor.extract_mineral_relationships(raw_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('minerals', result)
        self.assertIn('relationships', result)
    
    def test_extract_scientific_insights(self):
        """测试科学洞察提取"""
        raw_data = {
            'scientific_insights': {
                'significance': 'Important for astrobiology',
                'conclusions': 'Key findings'
            }
        }
        
        result = self.extractor.extract_scientific_insights(raw_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('significance', result)
        self.assertIn('conclusions', result)
    
    def test_extract_references(self):
        """测试参考文献提取"""
        raw_data = {
            'references': [
                {'title': 'Reference 1', 'content': 'Author et al. (2023)'}
            ]
        }
        
        result = self.extractor.extract_references(raw_data)
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


class TestResultValidator(TestCase):
    """测试结果验证器"""
    
    def setUp(self):
        """设置测试环境"""
        self.validator = ResultValidator()
    
    def test_validator_initialization(self):
        """测试验证器初始化"""
        self.assertIsNotNone(self.validator)
    
    def test_validate_result(self):
        """测试结果验证"""
        from ..direct_processing.data_extractor import StructuredData
        
        data = StructuredData(
            meteorite_data={'name': 'Test Meteorite'},
            organic_compounds={'compounds': 'amino acids'},
            mineral_relationships={},
            scientific_insights={'significance': 'Important'},
            references=[]
        )
        
        result = self.validator.validate_result(data)
        
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.validation_checks)
        self.assertGreaterEqual(result.confidence_score, 0.0)
        self.assertLessEqual(result.confidence_score, 1.0)
    
    def test_check_meteorite_classification(self):
        """测试陨石分类检查"""
        meteorite_data = {'classification': 'chondrite'}
        result = self.validator._check_meteorite_classification(meteorite_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.check_name, 'meteorite_classification')
    
    def test_check_organic_consistency(self):
        """测试有机化合物一致性检查"""
        organic_data = {'compounds': 'amino acids'}
        result = self.validator._check_organic_consistency(organic_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.check_name, 'organic_consistency')
    
    def test_check_mineral_consistency(self):
        """测试矿物一致性检查"""
        mineral_data = {'minerals': 'olivine, pyroxene'}
        result = self.validator._check_mineral_consistency(mineral_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.check_name, 'mineral_consistency')


class TestUtils(TestCase):
    """测试工具函数"""
    
    def test_validate_pdf_file_valid(self):
        """测试有效PDF文件验证"""
        # 创建临时PDF文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b'%PDF-1.4\n%Test PDF content')
            temp_file_path = temp_file.name
        
        try:
            result = validate_pdf_file(temp_file_path)
            
            self.assertIsInstance(result, dict)
            self.assertIn('valid', result)
            self.assertIn('file_exists', result)
            self.assertIn('file_size', result)
        finally:
            os.unlink(temp_file_path)
    
    def test_validate_pdf_file_nonexistent(self):
        """测试不存在文件验证"""
        result = validate_pdf_file('nonexistent.pdf')
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result['valid'])
        self.assertFalse(result['file_exists'])
    
    def test_validate_pdf_file_empty(self):
        """测试空文件验证"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            result = validate_pdf_file(temp_file_path)
            
            self.assertIsInstance(result, dict)
            self.assertFalse(result['valid'])
        finally:
            os.unlink(temp_file_path)


class TestModels(TestCase):
    """测试数据模型"""
    
    def test_direct_processing_result_creation(self):
        """测试直接处理结果创建"""
        result = DirectProcessingResult.objects.create(
            document_path='test.pdf',
            document_title='Test Document',
            processing_time=10.5,
            confidence_score=0.85,
            meteorite_data={'name': 'Test Meteorite'},
            organic_compounds={'compounds': 'amino acids'},
            mineral_relationships={},
            scientific_insights={'significance': 'Important'},
            validation_checks=[],
            status='completed'
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result.document_title, 'Test Document')
        self.assertEqual(result.confidence_score, 0.85)
        self.assertEqual(result.status, 'completed')
    
    def test_processing_task_creation(self):
        """测试处理任务创建"""
        task = ProcessingTask.objects.create(
            task_id='test-task-123',
            document_path='test.pdf',
            options={'focus': 'meteorite'},
            status='pending'
        )
        
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, 'test-task-123')
        self.assertEqual(task.status, 'pending')
    
    def test_processing_task_status_update(self):
        """测试处理任务状态更新"""
        task = ProcessingTask.objects.create(
            task_id='test-task-456',
            document_path='test.pdf',
            status='pending'
        )
        
        task.start_processing()
        self.assertEqual(task.status, 'processing')
        
        task.fail_processing('Test error')
        self.assertEqual(task.status, 'failed')
        self.assertEqual(task.error_message, 'Test error')


if __name__ == '__main__':
    unittest.main()
