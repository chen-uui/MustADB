"""
验证HuggingFace Token的工具脚本
用于验证HuggingFace Hub的访问令牌是否有效
"""
from huggingface_hub import HfApi

token = ""
print(HfApi().whoami(token=token))  # 返回用户信息说明 token 有效

