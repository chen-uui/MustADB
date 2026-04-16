"""
统一RAG服务测试
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock

class UnifiedRAGTestCase(TestCase):
    """统一RAG服务测试"""
    
    def setUp(self):
        self.client = Client()
        self.search_url = '/api/pdf/unified/search/'
        self.question_url = '/api/pdf/unified/question/'
        self.extract_url = '/api/pdf/unified/extract/'
        self.status_url = '/api/pdf/unified/status/'
    
    @patch('pdf_processor.views_unified_rag.unified_rag_service')
    def test_search_success(self, mock_service):
        """测试搜索成功"""
        # 模拟服务
        mock_service._is_initialized = True
        mock_service.search.return_value = [
            MagicMock(
                content="测试内容",
                title="测试标题",
                document_id="test_doc",
                page=1,
                chunk_index=0,
                score=0.9,
                metadata={}
            )
        ]
        
        # 发送请求
        response = self.client.post(
            self.search_url,
            data=json.dumps({
                'query': 'meteorite',
                'strategy': 'comprehensive',
                'limit': 10
            }),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['segments']), 1)
    
    def test_search_invalid_query(self):
        """测试无效查询"""
        response = self.client.post(
            self.search_url,
            data=json.dumps({
                'query': '',
                'strategy': 'comprehensive'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'INVALID_QUERY')
    
    @patch('pdf_processor.views_unified_rag.unified_rag_service')
    def test_question_success(self, mock_service):
        """测试问答成功"""
        # 模拟服务
        mock_service._is_initialized = True
        mock_answer = MagicMock()
        mock_answer.answer = "测试答案"
        mock_answer.sources = []
        mock_answer.confidence = 0.8
        mock_answer.total_contexts = 1
        mock_service.ask_question.return_value = mock_answer
        
        # 发送请求
        response = self.client.post(
            self.question_url,
            data=json.dumps({
                'question': '什么是陨石？'
            }),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['answer'], "测试答案")
    
    def test_question_invalid_question(self):
        """测试无效问题"""
        response = self.client.post(
            self.question_url,
            data=json.dumps({
                'question': ''
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'INVALID_QUESTION')
    
    @patch('pdf_processor.views_unified_rag.unified_rag_service')
    def test_extract_success(self, mock_service):
        """测试数据提取成功"""
        # 模拟服务
        mock_service._is_initialized = True
        mock_meteorite_data = MagicMock()
        mock_meteorite_data.name = "测试陨石"
        mock_meteorite_data.classification = "碳质球粒陨石"
        mock_meteorite_data.discovery_location = "测试地点"
        mock_meteorite_data.origin = "小行星带"
        mock_meteorite_data.organic_compounds = {"氨基酸": "检测到"}
        mock_meteorite_data.contamination_exclusion_method = "严格清洁"
        mock_meteorite_data.references = [{"title": "测试论文"}]
        mock_service.extract_meteorite_data.return_value = mock_meteorite_data
        
        # 发送请求
        response = self.client.post(
            self.extract_url,
            data=json.dumps({
                'content': '这是一个关于陨石的测试内容'
            }),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['name'], "测试陨石")
    
    def test_extract_invalid_content(self):
        """测试无效内容"""
        response = self.client.post(
            self.extract_url,
            data=json.dumps({
                'content': ''
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'INVALID_CONTENT')
    
    def test_service_status(self):
        """测试服务状态"""
        response = self.client.get(self.status_url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('weaviate_connected', data['data'])
        self.assertIn('embedding_available', data['data'])
        self.assertIn('llm_connected', data['data'])
    
    def test_invalid_json(self):
        """测试无效JSON"""
        response = self.client.post(
            self.search_url,
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'INVALID_JSON')
