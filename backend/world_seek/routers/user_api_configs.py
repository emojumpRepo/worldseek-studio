from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from world_seek.models.user_api_configs import (
    ApiKeys,
    ApiKeysConfigForm,
    ApiKeysConfigResponse,
)
from world_seek.constants import ERROR_MESSAGES
from world_seek.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api-keys", response_model=ApiKeysConfigResponse)
async def get_api_keys_config(
    user=Depends(get_verified_user)
) -> ApiKeysConfigResponse:
    """
    获取API密钥配置（脱敏后）
    
    所有已验证用户都可以查看配置状态（但看不到完整密钥）
    
    Args:
        user: 当前用户
        
    Returns:
        API密钥配置（脱敏后）
    """
    log.info(f"获取API密钥配置: 用户ID={user.id}, 角色={user.role}")
    
    try:
        config = ApiKeys.get_config()
        response = ApiKeysConfigResponse.from_config(config)
        log.info(f"成功获取API密钥配置")
        return response
    except Exception as e:
        log.exception(f"获取API密钥配置时发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取API配置失败"
        )

@router.post("/api-keys", response_model=ApiKeysConfigResponse)
async def update_api_keys_config(
    form_data: ApiKeysConfigForm,
    user=Depends(get_admin_user)
) -> ApiKeysConfigResponse:
    """
    更新API密钥配置
    
    只有管理员可以更新API密钥配置
    
    Args:
        form_data: API配置表单数据
        user: 管理员用户
        
    Returns:
        更新后的API配置（脱敏后）
    """
    log.info(f"更新API密钥配置: 管理员ID={user.id}")
    
    try:
        # 验证输入数据
        if (not form_data.langflow_api_key and not form_data.langflow_base_url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要提供一项API配置"
            )
        
        # 更新配置
        success = ApiKeys.update_config(form_data)
        if success:
            # 返回更新后的配置
            config = ApiKeys.get_config()
            response = ApiKeysConfigResponse.from_config(config)
            log.info(f"成功更新API密钥配置")
            return response
        else:
            log.error(f"更新API密钥配置失败")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新API配置失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"更新API密钥配置时发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新API配置失败"
        ) 