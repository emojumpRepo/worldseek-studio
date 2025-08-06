import logging
from typing import Optional
from pydantic import BaseModel, ConfigDict

from world_seek.config import PersistentConfig
import os

log = logging.getLogger(__name__)

####################
# API Keys Config Models
####################

class ApiKeysConfigForm(BaseModel):
    langflow_api_key: Optional[str] = None
    langflow_base_url: Optional[str] = None
    fastgpt_api_key: Optional[str] = None
    fastgpt_base_url: Optional[str] = None

class ApiKeysConfigModel(ApiKeysConfigForm):
    model_config = ConfigDict(from_attributes=True)

class ApiKeysConfigResponse(BaseModel):
    # 响应时不显示完整的API key，只显示部分字符
    langflow_api_key_masked: Optional[str] = None
    langflow_base_url: Optional[str] = None
    fastgpt_api_key_masked: Optional[str] = None
    fastgpt_base_url: Optional[str] = None
    
    @classmethod
    def from_config(cls, config: ApiKeysConfigModel):
        """从配置创建响应对象，并对API key进行脱敏处理"""
        data = config.model_dump()
        
        # 对Langflow API key进行脱敏处理
        if data.get("langflow_api_key"):
            key = data["langflow_api_key"]
            if len(key) > 8:
                data["langflow_api_key_masked"] = key[:4] + "*" * (len(key) - 8) + key[-4:]
            else:
                data["langflow_api_key_masked"] = "*" * len(key)
        
        # 对FastGPT API key进行脱敏处理
        if data.get("fastgpt_api_key"):
            key = data["fastgpt_api_key"]
            if len(key) > 8:
                data["fastgpt_api_key_masked"] = key[:4] + "*" * (len(key) - 8) + key[-4:]
            else:
                data["fastgpt_api_key_masked"] = "*" * len(key)
        
        return cls(
            langflow_api_key_masked=data.get("langflow_api_key_masked"),
            langflow_base_url=data.get("langflow_base_url"),
            fastgpt_api_key_masked=data.get("fastgpt_api_key_masked"),
            fastgpt_base_url=data.get("fastgpt_base_url"),
        )

####################
# Persistent Config for API Keys
####################

# 创建持久化配置对象
LANGFLOW_API_KEY = PersistentConfig(
    "LANGFLOW_API_KEY",
    "api_keys.langflow.api_key", 
    os.environ.get("LANGFLOW_TOKEN", "")
)

LANGFLOW_BASE_URL = PersistentConfig(
    "LANGFLOW_BASE_URL",
    "api_keys.langflow.base_url",
    os.environ.get("LANGFLOW_API_BASE_URL", "")
)

FASTGPT_API_KEY = PersistentConfig(
    "FASTGPT_API_KEY", 
    "api_keys.fastgpt.api_key",
    os.environ.get("FASTGPT_TOKEN", "")
)

FASTGPT_BASE_URL = PersistentConfig(
    "FASTGPT_BASE_URL",
    "api_keys.fastgpt.base_url", 
    os.environ.get("FASTGPT_BASE_URL", "")
)

####################
# API Keys Manager
####################

class ApiKeysManager:
    @staticmethod
    def get_config() -> ApiKeysConfigModel:
        """获取API密钥配置"""
        try:
            return ApiKeysConfigModel(
                langflow_api_key=LANGFLOW_API_KEY.value,
                langflow_base_url=LANGFLOW_BASE_URL.value,
                fastgpt_api_key=FASTGPT_API_KEY.value,
                fastgpt_base_url=FASTGPT_BASE_URL.value
            )
        except Exception as e:
            log.exception(f"获取API密钥配置时发生错误: {e}")
            return ApiKeysConfigModel()
    
    @staticmethod
    def update_config(form_data: ApiKeysConfigForm) -> bool:
        """更新API密钥配置"""
        try:
            # 只更新提供的字段
            if form_data.langflow_api_key is not None:
                LANGFLOW_API_KEY.value = form_data.langflow_api_key
                LANGFLOW_API_KEY.save()
            
            if form_data.langflow_base_url is not None:
                LANGFLOW_BASE_URL.value = form_data.langflow_base_url
                LANGFLOW_BASE_URL.save()
            
            if form_data.fastgpt_api_key is not None:
                FASTGPT_API_KEY.value = form_data.fastgpt_api_key
                FASTGPT_API_KEY.save()
            
            if form_data.fastgpt_base_url is not None:
                FASTGPT_BASE_URL.value = form_data.fastgpt_base_url
                FASTGPT_BASE_URL.save()
            
            log.info("API密钥配置更新成功")
            return True
        except Exception as e:
            log.exception(f"更新API密钥配置时发生错误: {e}")
            return False
    
    @staticmethod
    def get_langflow_config() -> tuple[str, str]:
        """获取Langflow配置"""
        return LANGFLOW_API_KEY.value, LANGFLOW_BASE_URL.value
    
    @staticmethod
    def get_fastgpt_config() -> tuple[str, str]:
        """获取FastGPT配置"""
        return FASTGPT_API_KEY.value, FASTGPT_BASE_URL.value

# 导出管理器实例
ApiKeys = ApiKeysManager() 