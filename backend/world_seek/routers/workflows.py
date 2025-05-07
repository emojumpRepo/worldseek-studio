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
    
    log.info(f"开始执行工作流: ID={workflow_id}, 用户={user.id}, 时间={start_time}")
    
    # 记录消息数量和类型
    messages = form_data.get("messages", [])
    message_count = len(messages)
    log.info(f"工作流请求消息: 数量={message_count}")
    
    # 获取工作流
    workflow = Workflows.get_workflow_by_id(workflow_id)
    if not workflow:
        log.warning(f"工作流未找到: ID={workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        # 使用对象属性访问方式
        log.info(f"找到工作流: ID={workflow_id}, 名称={workflow.name}")
        log.info(f"工作流: {workflow}")
        log.info(f"工作流API路径: {workflow.api_path}")
        log.info(f"工作流App Token: {workflow.app_token}")
        
        base_url = "https://api.langflow.astra.datastax.com/lf/8f511d42-9db1-41c8-84cb-bd19dbd841f2/api/v1/run/"
        
        # 直接从workflow对象获取api_path
        api_path = workflow.api_path
        if not api_path:
            log.error(f"工作流API路径未配置: ID={workflow_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Langflow API path not configured for this workflow",
            )
        
        log.info(f"工作流API路径: {api_path}")
        
        # 获取App Token (同样直接从workflow对象获取)
        app_token = workflow.app_token
        if not app_token:
            # 尝试从params中获取（可选的备选方案）
            if hasattr(workflow, 'params') and workflow.params and "app_token" in workflow.params:
                app_token = workflow.params.get("app_token")
            
            if not app_token:
                log.error(f"工作流App Token未配置: ID={workflow_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="App Token not configured for this workflow",
                )
        
        # 不记录完整token，只记录长度和前几个字符用于调试
        token_prefix = app_token[:4] if len(app_token) > 4 else ""
        log.info(f"工作流Token: 长度={len(app_token)}, 前缀={token_prefix}***")
        
        # 获取参数
        params = form_data.get("params", {})
        stream = params.get("stream", False)
        
        log.info(f"工作流执行参数: stream={stream}, params={params}")
        
        # 准备发送给Langflow的数据
        langflow_data = {
            "input_value": messages,
            "input_type": "chat",
            "output_type": "chat",
        }
        
        log.info(f"准备调用Langflow API: base_url={base_url}, data长度={len(str(langflow_data))}")
        
        # 调用Langflow API (支持流式响应)
        try:
            api_call_start = time.time()
            log.info(f"开始调用Langflow API: 时间={api_call_start}")
            
            result = await call_langflow_api(base_url, api_path, app_token, langflow_data, stream=stream)
            
            api_call_end = time.time()
            api_call_duration = api_call_end - api_call_start
            
            if stream:
                log.info(f"Langflow API流式调用成功: 响应类型=StreamingResponse, 耗时={api_call_duration:.2f}秒")
            else:
                # 记录响应大小
                result_size = len(str(result))
                log.info(f"Langflow API调用成功: 响应大小={result_size}字节, 耗时={api_call_duration:.2f}秒")
            
            total_time = time.time() - start_time
            log.info(f"工作流执行完成: ID={workflow_id}, 总耗时={total_time:.2f}秒")
            
            return result
        except Exception as e:
            error_time = time.time()
            error_duration = error_time - start_time
            log.error(f"Langflow API调用失败: ID={workflow_id}, 错误={str(e)}, 已执行时间={error_duration:.2f}秒")
            
            # 检查是否是超时错误
            import asyncio
            if isinstance(e, asyncio.TimeoutError) or "timeout" in str(e).lower():
                log.error(f"工作流执行超时: ID={workflow_id}, 已执行时间={error_duration:.2f}秒")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calling Langflow API: {str(e)}",
            )
    except Exception as e:
        # 添加对工作流处理过程中的异常捕获
        log.exception(f"工作流处理过程异常: ID={workflow_id}, 错误类型={type(e).__name__}, 错误={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow processing error: {str(e)}",
        )
