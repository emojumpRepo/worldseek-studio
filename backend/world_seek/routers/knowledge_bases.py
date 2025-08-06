from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
import logging
import aiohttp

from world_seek.models.user_api_configs import ApiKeys
from world_seek.utils.auth import get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()

@router.get("/get_knowledge_bases", response_model=List[Dict[str, Any]])
async def get_fastgpt_knowledge_bases(
    user=Depends(get_verified_user)
) -> List[Dict[str, Any]]:
    """
    获取FastGPT知识库列表
    
    Args:
        user: 当前用户
        
    Returns:
        知识库列表
    """
    log.info(f"用户 {user.id} 请求FastGPT知识库列表")
    
    try:
        # 获取FastGPT配置
        fastgpt_api_key, fastgpt_base_url = ApiKeys.get_fastgpt_config()
        
        if not fastgpt_api_key or not fastgpt_base_url:
            log.warning("FastGPT API密钥或基础URL未配置")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='未配置FastGPT API密钥或基础URL，请联系管理员设置'
            )
        
        # 构建请求URL
        api_url = f"{fastgpt_base_url.rstrip('/')}/api/core/dataset/list?parentId="
        
        # 请求头
        headers = {
            'Authorization': f'Bearer {fastgpt_api_key}',
            'Content-Type': 'application/json'
        }
        
        # 发送HTTP请求
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 提取知识库信息
                    knowledge_bases = []
                    if isinstance(data, dict) and 'data' in data:
                        datasets = data.get('data', [])
                    elif isinstance(data, list):
                        datasets = data
                    else:
                        datasets = []
                    
                    for dataset in datasets:
                        knowledge_base = {
                            'id': dataset.get('_id', ''),
                            'name': dataset.get('name', ''),
                            'description': dataset.get('intro', ''),
                            'avatar': dataset.get('avatar', ''),
                            'vectorModel': dataset.get('vectorModel', {}),
                            'tags': dataset.get('tags', []),
                            'createTime': dataset.get('createTime', ''),
                            'updateTime': dataset.get('updateTime', ''),
                            'type': dataset.get('type', ''),
                            'status': dataset.get('status', '')
                        }
                        knowledge_bases.append(knowledge_base)
                    
                    log.info(f"成功获取到 {len(knowledge_bases)} 个知识库")
                    return knowledge_bases
                    
                elif response.status == 401:
                    log.error("FastGPT API密钥验证失败")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail='FastGPT API密钥验证失败，请联系管理员检查配置'
                    )
                else:
                    error_text = await response.text()
                    log.error(f"FastGPT API请求失败: 状态码={response.status}, 响应={error_text}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f'FastGPT服务请求失败: {response.status}'
                    )
                    
    except aiohttp.ClientError as e:
        log.exception(f"连接FastGPT服务时发生网络错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='无法连接到FastGPT服务，请检查网络连接'
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"获取FastGPT知识库列表时发生未知错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='获取知识库列表失败'
        )