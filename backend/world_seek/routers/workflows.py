from typing import Optional

from world_seek.workflows.workflows import (
    WorkflowForm,
    WorkflowModel,
    WorkflowResponse,
    Workflows,
)
from world_seek.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status


from world_seek.utils.auth import get_admin_user, get_verified_user
from world_seek.utils.access_control import has_access, has_permission
from world_seek.utils.workflow import call_langflow_api


router = APIRouter()


###########################
# GetWorkflows
###########################


@router.get("/", response_model=list[WorkflowResponse])
async def get_workflows(id: Optional[str] = None, user=Depends(get_verified_user)):
    print(f"get_workflows: {user}")
    return Workflows.get_workflows(user.id, user.role)


############################
# CreateNewWorkflow
############################


@router.post("/create", response_model=Optional[WorkflowModel])
async def create_new_workflow(
    request: Request,
    form_data: WorkflowForm,
    user=Depends(get_verified_user),
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.workflows", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    workflow = Workflows.get_workflow_by_id(form_data.id)
    if workflow:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.WORKFLOW_ID_TAKEN,
        )

    else:
        workflow = Workflows.insert_new_workflow(form_data, user.id)
        if workflow:
            return workflow
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.DEFAULT(),
            )


###########################
# GetWorkflowById
###########################


# Note: We're not using the typical url path param here, but instead using a query parameter to allow '/' in the id
@router.get("/workflow", response_model=Optional[WorkflowResponse])
async def get_workflow_by_id(id: str, user=Depends(get_verified_user)):
    workflow = Workflows.get_workflow_by_id(id)
    if workflow:
        if (
            user.role == "admin"
            or workflow.user_id == user.id
            or has_access(user.id, "read", workflow.access_control)
        ):
            return workflow
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateWorkflowById
############################


@router.post("/workflow/update", response_model=Optional[WorkflowModel])
async def update_workflow_by_id(
    id: str,
    form_data: WorkflowForm,
    user=Depends(get_verified_user),
):
    workflow = Workflows.get_workflow_by_id(id)
    print(f"update_workflow: {workflow}")

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    workflow = Workflows.update_workflow_by_id(id, form_data)
    return workflow


############################
# DeleteWorkflowById
############################


@router.delete("/workflow/delete", response_model=bool)
async def delete_workflow_by_id(id: str, user=Depends(get_verified_user)):
    workflow = Workflows.get_workflow_by_id(id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = Workflows.delete_workflow_by_id(id)
    return result


@router.delete("/delete/all", response_model=bool)
async def delete_all_workflows(user=Depends(get_admin_user)):
    result = Workflows.delete_all_workflows()
    return result


############################
# RunWorkflow
############################


@router.post("/run", response_model=dict)
async def run_workflow(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """
    向Langflow工作流发送聊天请求并接收回复
    
    form_data应包含:
    - workflow_id: 工作流ID
    - messages: 消息列表
    - params: 可选参数
        - stream: 布尔值，是否使用流式响应
    """
    import logging
    import time
    from world_seek.env import SRC_LOG_LEVELS
    
    log = logging.getLogger(__name__)
    log.setLevel(SRC_LOG_LEVELS.get("LANGFLOW", SRC_LOG_LEVELS["MAIN"]))
    
    start_time = time.time()
    workflow_id = form_data.get("workflow_id")
    
    log.info(f"执行工作流: ID={workflow_id}, 用户={user.id}")
    
    # 获取最新的消息内容
    latest_message = ""
    messages = form_data.get("messages", [])
    log.info(f"消息记录messages: {messages}")
    
    # 从消息列表中找到最后一个role为"user"的消息
    if messages and isinstance(messages, list):
        # 从后向前遍历，找到第一个role为user的消息
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user" and "content" in msg:
                latest_message_obj = msg
                latest_message = msg["content"]
                log.info(f"找到最新用户消息: {latest_message_obj}")
                break
    
    # 检查最新消息是否为空，如果为空直接返回错误
    if not latest_message or latest_message.strip() == "":
        log.warning(f"工作流请求无有效用户消息: ID={workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未找到有效的用户消息",
        )
    
    log.info(f"用户消息内容: {latest_message[:50]}...")
    
    # 获取工作流
    workflow = Workflows.get_workflow_by_id(workflow_id)
    if not workflow:
        log.warning(f"工作流未找到: ID={workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        # 简化的工作流日志
        log.info(f"工作流信息: ID={workflow_id}, 名称={workflow.name}")
        
        # 准备API完整URL - 直接使用workflow.api_path作为完整URL
        api_url = workflow.api_path
        
        # 检查API路径格式 - 如果不是完整URL，则构建完整URL
        if not api_url:
            log.error(f"API路径未配置: ID={workflow_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Langflow API path not configured for this workflow",
            )
        
        # 如果api_url不以http开头，则添加基础URL
        if not api_url.startswith(('http://', 'https://')):
            api_url = f"http://8.130.43.71:7860/api/v1/run/{api_url}"
        
        log.info(f"完整API URL: {api_url}")
        
        # 获取App Token (同样直接从workflow对象获取)
        app_token = workflow.app_token
        if not app_token:
            # 尝试从params中获取（可选的备选方案）
            if hasattr(workflow, 'params') and workflow.params and "app_token" in workflow.params:
                app_token = workflow.params.get("app_token")
        
        # 获取参数
        params = form_data.get("params", {})
        stream = params.get("stream", False)
        
        # 设置较长的超时时间
        timeout = params.get("timeout", 180)  # 默认3分钟
        
        # 准备发送给Langflow的数据
        langflow_data = {
            "input_value": latest_message,
            "input_type": "chat",
            "output_type": "chat",
        }
        
        # 调用Langflow API (支持流式响应)
        try:
            api_call_start = time.time()
            log.info(f"调用Langflow API: URL={api_url}, 流式={stream}, 超时={timeout}秒")
            
            # 直接调用API，使用完整URL - 设置为空的base_url和api_url作为path
            result = await call_langflow_api("", api_url, app_token, langflow_data, stream=stream, timeout=timeout)
            
            api_call_end = time.time()
            api_call_duration = api_call_end - api_call_start
            
            log.info(f"API调用成功: 耗时={api_call_duration:.2f}秒")
            
            return result
        except Exception as e:
            error_time = time.time()
            error_duration = error_time - start_time
            log.error(f"API调用失败: {str(e)}, 耗时={error_duration:.2f}秒")
            
            # 检查是否是超时错误
            import asyncio
            if isinstance(e, asyncio.TimeoutError) or "timeout" in str(e).lower():
                log.error(f"API调用超时: 已用时间={error_duration:.2f}秒")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calling Langflow API: {str(e)}",
            )
    except Exception as e:
        # 添加对工作流处理过程中的异常捕获
        log.exception(f"工作流处理异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow processing error: {str(e)}",
        )
