"""
直接处理系统的集成测试
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User

from ..direct_processing.document_processor import DirectDocumentProcessor
from ..models.direct_processing_models import (
    DirectProcessingResult, 
    ProcessingTask, 
    ProcessingLog,
    SystemConfiguration
)


class TestDirectProcessingIntegration(TransactionTestCase):
    """测试直接处理系统集成"""
    
    def setUp(self):
        """设置测试环境"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 创建测试PDF文件
        self.test_pdf_content = b'%PDF-1.4\n%Test PDF content for integration testing'
        self.test_pdf_file = SimpleUploadedFile(
            'test.pdf',
            self.test_pdf_content,
            content_type='application/pdf'
        )
    
    def tearDown(self):
        """清理测试环境"""
        # 清理测试文件
        if hasattr(self, 'test_pdf_file'):
            self.test_pdf_file.close()
    
    @patch('pdf_processor.direct_processing.document_processor.extract_pdf_text')
    @patch('pdf_processor.direct_processing.llm_analyzer.requests.post')
    def test_complete_processing_workflow(self, mock_post, mock_extract_text):
        """测试完整的处理工作流程"""
        # 模拟PDF文本提取
        mock_extract_text.return_value = """
        This is a test meteorite paper.
        Meteorite Name: Test Meteorite
        Classification: Chondrite
        Location: Antarctica
        Organic compounds: amino acids, proteins
        Mineral relationships: olivine-pyroxene association
        Scientific significance: Important for astrobiology
        """
        
        # 模拟LLM响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': json.dumps({
                'meteorite_data': {
                    'name': 'Test Meteorite',
                    'classification': 'Chondrite',
                    'location': 'Antarctica'
                },
                'organic_compounds': {
                    'compounds': 'amino acids, proteins',
                    'concentration': '10 ppm'
                },
                'mineral_relationships': {
                    'minerals': 'olivine, pyroxene',
                    'relationships': 'crystallization sequence'
                },
                'scientific_insights': {
                    'significance': 'Important for astrobiology',
                    'conclusions': 'Key findings'
                },
                'references': [
                    {'title': 'Reference 1', 'content': 'Author et al. (2023)'}
                ]
            })
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # 创建处理器
        processor = DirectDocumentProcessor()
        
        # 执行处理
        result = processor.process_document('test.pdf')
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result.document_path, 'test.pdf')
        self.assertGreater(result.processing_time, 0)
        self.assertGreater(result.confidence_score, 0)
        self.assertIsNotNone(result.results)
    
    def test_api_endpoint_process_document(self):
        """测试API端点 - 处理文档"""
        # 登录用户
        self.client.force_login(self.user)
        
        # 准备请求数据
        data = {
            'options': json.dumps({
                'focus': 'comprehensive',
                'detail_level': 'high'
            })
        }
        
        with patch('pdf_processor.views.direct_processing_views.DirectDocumentProcessor') as mock_processor:
            # 模拟处理结果
            mock_result = Mock()
            mock_result.document_path = 'test.pdf'
            mock_result.processing_time = 10.5
            mock_result.confidence_score = 0.85
            mock_result.results = Mock()
            mock_result.results.data = Mock()
            mock_result.results.data.meteorite_data = {'name': 'Test Meteorite'}
            mock_result.results.data.organic_compounds = {'compounds': 'amino acids'}
            mock_result.results.data.mineral_relationships = {}
            mock_result.results.data.scientific_insights = {'significance': 'Important'}
            mock_result.results.validation_checks = []
            mock_result.results.validation_notes = 'Validation completed'
            
            mock_processor.return_value.process_document.return_value = mock_result
            
            # 发送请求
            response = self.client.post(
                '/api/direct-processing/process/',
                data=data,
                files={'file': self.test_pdf_file}
            )
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.content)
            self.assertIn('task_id', response_data)
            self.assertEqual(response_data['status'], 'processing')
    
    def test_api_endpoint_get_processing_status(self):
        """测试API端点 - 获取处理状态"""
        # 创建测试任务
        task = ProcessingTask.objects.create(
            task_id='test-task-123',
            document_path='test.pdf',
            status='processing',
            progress=50.0,
            current_step='Analyzing document',
            created_by=self.user
        )
        
        # 发送请求
        response = self.client.get(f'/api/direct-processing/status/{task.task_id}/')
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['task_id'], task.task_id)
        self.assertEqual(response_data['status'], 'processing')
        self.assertEqual(response_data['progress'], 50.0)
        self.assertEqual(response_data['current_step'], 'Analyzing document')
    
    def test_api_endpoint_get_processing_result(self):
        """测试API端点 - 获取处理结果"""
        # 创建测试结果
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
            status='completed',
            created_by=self.user
        )
        
        # 发送请求
        response = self.client.get(f'/api/direct-processing/result/{result.id}/')
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['id'], result.id)
        self.assertEqual(response_data['document_title'], 'Test Document')
        self.assertEqual(response_data['confidence_score'], 0.85)
        self.assertEqual(response_data['status'], 'completed')
    
    def test_api_endpoint_batch_process(self):
        """测试API端点 - 批量处理"""
        # 登录用户
        self.client.force_login(self.user)
        
        # 准备多个测试文件
        test_files = []
        for i in range(3):
            test_file = SimpleUploadedFile(
                f'test{i}.pdf',
                self.test_pdf_content,
                content_type='application/pdf'
            )
            test_files.append(test_file)
        
        try:
            with patch('pdf_processor.views.direct_processing_views.DirectDocumentProcessor') as mock_processor:
                # 模拟处理结果
                mock_result = Mock()
                mock_result.document_path = 'test.pdf'
                mock_result.processing_time = 10.5
                mock_result.confidence_score = 0.85
                mock_result.results = Mock()
                mock_result.results.data = Mock()
                mock_result.results.data.meteorite_data = {'name': 'Test Meteorite'}
                mock_result.results.data.organic_compounds = {'compounds': 'amino acids'}
                mock_result.results.data.mineral_relationships = {}
                mock_result.results.data.scientific_insights = {'significance': 'Important'}
                mock_result.results.validation_checks = []
                mock_result.results.validation_notes = 'Validation completed'
                
                mock_processor.return_value.process_document.return_value = mock_result
                
                # 发送请求
                response = self.client.post(
                    '/api/direct-processing/batch/',
                    files={'files': test_files}
                )
                
                # 验证响应
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.content)
                self.assertIn('task_ids', response_data)
                self.assertEqual(len(response_data['task_ids']), 3)
        finally:
            # 清理测试文件
            for test_file in test_files:
                test_file.close()
    
    def test_api_endpoint_get_processing_history(self):
        """测试API端点 - 获取处理历史"""
        # 创建测试结果
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
            status='completed',
            created_by=self.user
        )
        
        # 发送请求
        response = self.client.get('/api/direct-processing/history/')
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('results', response_data)
        self.assertGreater(len(response_data['results']), 0)
    
    def test_api_endpoint_get_processing_statistics(self):
        """测试API端点 - 获取处理统计"""
        # 发送请求
        response = self.client.get('/api/direct-processing/statistics/')
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('statistics', response_data)
        self.assertIn('period', response_data)
    
    def test_database_models_integration(self):
        """测试数据库模型集成"""
        # 创建处理任务
        task = ProcessingTask.objects.create(
            task_id='test-task-789',
            document_path='test.pdf',
            options={'focus': 'meteorite'},
            status='pending',
            created_by=self.user
        )
        
        # 创建处理日志
        log = ProcessingLog.objects.create(
            task=task,
            level='INFO',
            message='Test log message'
        )
        
        # 创建处理结果
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
            status='completed',
            created_by=self.user
        )
        
        # 更新任务状态
        task.complete_processing(result)
        
        # 验证数据库关系
        self.assertEqual(task.result, result)
        self.assertEqual(task.status, 'completed')
        self.assertEqual(log.task, task)
        
        # 验证结果方法
        summary = result.get_processing_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn('document_title', summary)
        self.assertIn('confidence_score', summary)
        
        # 验证验证状态
        validation_status = result.get_validation_status()
        self.assertIsInstance(validation_status, bool)
    
    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 测试无效文件上传
        invalid_file = SimpleUploadedFile(
            'test.txt',
            b'This is not a PDF file',
            content_type='text/plain'
        )
        
        self.client.force_login(self.user)
        
        response = self.client.post(
            '/api/direct-processing/process/',
            files={'file': invalid_file}
        )
        
        # 验证错误响应
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        
        # 清理
        invalid_file.close()
    
    def test_performance_integration(self):
        """测试性能集成"""
        import time
        
        # 测试处理时间
        start_time = time.time()
        
        with patch('pdf_processor.direct_processing.document_processor.extract_pdf_text') as mock_extract_text:
            mock_extract_text.return_value = "Test content"
            
            with patch('pdf_processor.direct_processing.llm_analyzer.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {'response': '{"test": "data"}'}
                mock_response.raise_for_status.return_value = None
                mock_post.return_value = mock_response
                
                processor = DirectDocumentProcessor()
                result = processor.process_document('test.pdf')
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                # 验证处理时间合理
                self.assertLess(processing_time, 5.0)  # 应该在5秒内完成
                self.assertIsNotNone(result)


class TestSystemConfigurationIntegration(TestCase):
    """测试系统配置集成"""
    
    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
    
    def test_system_configuration_creation(self):
        """测试系统配置创建"""
        config = SystemConfiguration.objects.create(
            key='test_config',
            value='test_value',
            description='Test configuration',
            config_type='string'
        )
        
        self.assertIsNotNone(config)
        self.assertEqual(config.key, 'test_config')
        self.assertEqual(config.value, 'test_value')
        self.assertEqual(config.get_typed_value(), 'test_value')
    
    def test_system_configuration_types(self):
        """测试系统配置类型"""
        # 测试整数类型
        int_config = SystemConfiguration.objects.create(
            key='test_int',
            value='123',
            config_type='integer'
        )
        self.assertEqual(int_config.get_typed_value(), 123)
        
        # 测试浮点数类型
        float_config = SystemConfiguration.objects.create(
            key='test_float',
            value='123.45',
            config_type='float'
        )
        self.assertEqual(float_config.get_typed_value(), 123.45)
        
        # 测试布尔类型
        bool_config = SystemConfiguration.objects.create(
            key='test_bool',
            value='true',
            config_type='boolean'
        )
        self.assertEqual(bool_config.get_typed_value(), True)
        
        # 测试JSON类型
        json_config = SystemConfiguration.objects.create(
            key='test_json',
            value='{"test": "data"}',
            config_type='json'
        )
        self.assertEqual(json_config.get_typed_value(), {'test': 'data'})


if __name__ == '__main__':
    unittest.main()
