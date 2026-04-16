"""
LLaMA模型配置
定义不同场景下的生成参数配置
"""

class Llama3Config:
    """LLaMA3模型配置类"""
    
    @staticmethod
    def get_generation_params(scenario: str = "general") -> dict:
        """
        获取指定场景下的生成参数
        
        Args:
            scenario: 场景名称
            
        Returns:
            dict: 生成参数配置
        """
        configs = {
            "general": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2000,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0
            },
            "data_extraction": {
                "temperature": 0.1,  # 低温度确保一致性
                "top_p": 0.9,
                "max_tokens": 2000,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0
            },
            "creative_writing": {
                "temperature": 0.9,
                "top_p": 0.95,
                "max_tokens": 3000,
                "presence_penalty": 0.5,
                "frequency_penalty": 0.3
            },
            "code_generation": {
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 2500,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0
            },
            "academic_analysis": {
                "temperature": 0.3,
                "top_p": 0.85,
                "max_tokens": 2500,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0
            },
            "general_academic": {
                "temperature": 0.3,
                "top_p": 0.85,
                "max_tokens": 2000,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0
            }
        }
        
        return configs.get(scenario, configs["general"])
    
    @staticmethod
    def get_model_config(model_name: str = "llama3.1:8b-instruct-q4_K_M") -> dict:
        """
        获取模型配置
        
        Args:
            model_name: 模型名称
            
        Returns:
            dict: 模型配置
        """
        model_configs = {
            "llama3.1:8b-instruct-q4_K_M": {
                "name": "llama3.1:8b-instruct-q4_K_M",
                "context_length": 8192,
                "quantization": "4-bit",
                "recommended_scenarios": ["general", "data_extraction", "academic_analysis"]
            },
            "llama3:8b-instruct-q4_K_M": {
                "name": "llama3:8b-instruct-q4_K_M",
                "context_length": 8192,
                "quantization": "4-bit",
                "recommended_scenarios": ["general", "data_extraction", "academic_analysis"]
            },
            "llama3:70b-instruct-q4_K_M": {
                "name": "llama3:70b-instruct-q4_K_M",
                "context_length": 8192,
                "quantization": "4-bit",
                "recommended_scenarios": ["creative_writing", "complex_analysis"]
            }
        }
        
        return model_configs.get(model_name, model_configs["llama3.1:8b-instruct-q4_K_M"])