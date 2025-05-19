from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
import logging
import time
from datetime import datetime

from world_seek.workflows.workflows import (
    WorkflowForm,
    WorkflowModel,
    WorkflowResponse,
    Workflows,
)
from world_seek.constants import ERROR_MESSAGES
from world_seek.utils.auth import get_admin_user, get_verified_user
from world_seek.utils.access_control import has_access, has_permission
from world_seek.utils.workflow import call_langflow_api
from world_seek.env import SRC_LOG_LEVELS

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("LANGFLOW", SRC_LOG_LEVELS["MAIN"]))

# 常量定义
DEFAULT_TIMEOUT = 180  # 默认超时时间(秒)
DEFAULT_LANGFLOW_URL = "http://localhost:7860/api/v1/run/43dac7b4-e492-4c91-ad2e-d06bd0921303"

router = APIRouter()

###########################
# GetWorkflows
###########################

@router.get("/", response_model=List[WorkflowResponse])
async def get_workflows(
    id: Optional[str] = None,
    user=Depends(get_verified_user)
) -> List[WorkflowResponse]:
    """
    获取工作流列表
    
    Args:
        id: 可选的工作流ID
        user: 当前用户
        
    Returns:
        工作流列表
    """
    log.info(f"获取工作流列表: 用户ID={user.id}, 角色={user.role}")
    return Workflows.get_workflows(user.id, user.role)

############################
# CreateNewWorkflow
############################

@router.post("/create", response_model=Optional[WorkflowModel])
async def create_new_workflow(
    request: Request,
    form_data: WorkflowForm,
    user=Depends(get_verified_user),
) -> Optional[WorkflowModel]:
    """
    创建新工作流
    
    Args:
        request: 请求对象
        form_data: 工作流表单数据
        user: 当前用户
        
    Returns:
        创建的工作流模型
        
    Raises:
        HTTPException: 当用户无权限或工作流ID已存在时
    """
    log.info(f"创建新工作流: 用户ID={user.id}, 角色={user.role}")
    
    # 权限检查
    if user.role != "admin" and not has_permission(
        user.id, "workspace.workflows", request.app.state.config.USER_PERMISSIONS
    ):
        log.warning(f"用户无权限创建工作流: 用户ID={user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    # 检查工作流ID是否已存在
    workflow = Workflows.get_workflow_by_id(form_data.id)
    if workflow:
        log.warning(f"工作流ID已存在: ID={form_data.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.WORKFLOW_ID_TAKEN,
        )

    # 创建新工作流
    workflow = Workflows.insert_new_workflow(form_data, user.id)
    if workflow:
        log.info(f"工作流创建成功: ID={workflow.id}")
        return workflow
    else:
        log.error(f"工作流创建失败: ID={form_data.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

###########################
# GetWorkflowById
###########################

@router.get("/workflow", response_model=Optional[WorkflowResponse])
async def get_workflow_by_id(
    id: str,
    user=Depends(get_verified_user)
) -> Optional[WorkflowResponse]:
    """
    通过ID获取工作流
    
    Args:
        id: 工作流ID
        user: 当前用户
        
    Returns:
        工作流响应对象
        
    Raises:
        HTTPException: 当工作流不存在或用户无权限时
    """
    log.info(f"获取工作流: ID={id}, 用户ID={user.id}")
    
    workflow = Workflows.get_workflow_by_id(id)
    if not workflow:
        log.warning(f"工作流不存在: ID={id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
        
    # 权限检查
    if (
        user.role == "admin"
        or workflow.user_id == user.id
        or has_access(user.id, "read", workflow.access_control)
    ):
        log.info(f"工作流获取成功: ID={id}")
        return workflow
    else:
        log.warning(f"用户无权限访问工作流: ID={id}, 用户ID={user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

############################
# UpdateWorkflowById
############################

@router.post("/workflow/update", response_model=Optional[WorkflowModel])
async def update_workflow_by_id(
    id: str,
    form_data: WorkflowForm,
    user=Depends(get_verified_user),
) -> Optional[WorkflowModel]:
    """
    更新工作流
    
    Args:
        id: 工作流ID
        form_data: 工作流表单数据
        user: 当前用户
        
    Returns:
        更新后的工作流模型
        
    Raises:
        HTTPException: 当工作流不存在或用户无权限时
    """
    log.info(f"更新工作流: ID={id}, 用户ID={user.id}")
    
    workflow = Workflows.get_workflow_by_id(id)
    if not workflow:
        log.warning(f"工作流不存在: ID={id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if user.role != "admin":
        log.warning(f"用户无权限更新工作流: ID={id}, 用户ID={user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    workflow = Workflows.update_workflow_by_id(id, form_data)
    log.info(f"工作流更新成功: ID={id}")
    return workflow

############################
# DeleteWorkflowById
############################

@router.delete("/workflow/delete", response_model=bool)
async def delete_workflow_by_id(
    id: str,
    user=Depends(get_verified_user)
) -> bool:
    """
    删除工作流
    
    Args:
        id: 工作流ID
        user: 当前用户
        
    Returns:
        删除是否成功
        
    Raises:
        HTTPException: 当工作流不存在或用户无权限时
    """
    log.info(f"删除工作流: ID={id}, 用户ID={user.id}")
    
    workflow = Workflows.get_workflow_by_id(id)
    if not workflow:
        log.warning(f"工作流不存在: ID={id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if user.role != "admin":
        log.warning(f"用户无权限删除工作流: ID={id}, 用户ID={user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = Workflows.delete_workflow_by_id(id)
    log.info(f"工作流删除{'成功' if result else '失败'}: ID={id}")
    return result

@router.delete("/delete/all", response_model=bool)
async def delete_all_workflows(
    user=Depends(get_admin_user)
) -> bool:
    """
    删除所有工作流
    
    Args:
        user: 管理员用户
        
    Returns:
        删除是否成功
    """
    log.info(f"删除所有工作流: 用户ID={user.id}")
    result = Workflows.delete_all_workflows()
    log.info(f"所有工作流删除{'成功' if result else '失败'}")
    return result

############################
# RunWorkflow
############################

@router.post("/run", response_model=Dict[str, Any])
async def run_workflow(
    request: Request,
    form_data: Dict[str, Any],
    user=Depends(get_verified_user),
) -> Dict[str, Any]:
    """
    运行工作流
    
    Args:
        request: 请求对象
        form_data: 包含工作流ID、消息和参数的字典
        user: 当前用户
        
    Returns:
        工作流执行结果
        
    Raises:
        HTTPException: 当工作流不存在、无有效消息或执行出错时
    """
    start_time = time.time()
    workflow_id = form_data.get("workflow_id")
    
    log.info(f"执行工作流: ID={workflow_id}, 用户ID={user.id}")
    
    # 获取最新消息
    messages = form_data.get("messages", [])
    latest_message = ""
    
    if messages and isinstance(messages, list):
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user" and "content" in msg:
                latest_message = msg["content"]
                log.info(f"找到最新用户消息: {msg}")
                break
    
    if not latest_message or latest_message.strip() == "":
        log.warning(f"工作流请求无有效用户消息: ID={workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未找到有效的用户消息",
        )
    
    # 获取工作流
    workflow = Workflows.get_workflow_by_id(workflow_id)
    if not workflow:
        log.warning(f"工作流未找到: ID={workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        # 准备API URL
        api_url = workflow.api_path
        if not api_url:
            log.error(f"API路径未配置: ID={workflow_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Langflow API path not configured for this workflow",
            )
        
        if not api_url.startswith(('http://', 'https://')):
            api_url = DEFAULT_LANGFLOW_URL
        
        log.info(f"完整API URL: {api_url}")
        
        # 获取App Token
        app_token = workflow.app_token
        if not app_token and hasattr(workflow, 'params') and workflow.params:
            app_token = workflow.params.get("app_token")
        
        # 获取参数
        params = form_data.get("params", {})
        stream = params.get("stream", False)
        timeout = params.get("timeout", DEFAULT_TIMEOUT)
        
        # 准备请求数据
        langflow_data = {
            "input_value": latest_message,
            "input_type": "chat",
            "output_type": "chat",
        }
        
        # 调用Langflow API
        try:
            api_call_start = time.time()
            log.info(f"调用Langflow API: URL={api_url}, 流式={stream}, 超时={timeout}秒")
            
            result = await call_langflow_api("", api_url, app_token, langflow_data, stream=stream, timeout=timeout)
            
            api_call_duration = time.time() - api_call_start
            log.info(f"API调用成功: 耗时={api_call_duration:.2f}秒")
            
            return result
            
        except Exception as e:
            error_duration = time.time() - start_time
            log.error(f"API调用失败: {str(e)}, 耗时={error_duration:.2f}秒")
            
            if isinstance(e, asyncio.TimeoutError) or "timeout" in str(e).lower():
                log.error(f"API调用超时: 已用时间={error_duration:.2f}秒")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calling Langflow API: {str(e)}",
            )
            
    except Exception as e:
        log.exception(f"工作流处理异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow processing error: {str(e)}",
        )
