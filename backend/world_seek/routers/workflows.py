from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
import logging
import time
from datetime import datetime
from fastapi.responses import JSONResponse
import aiohttp
import json

from world_seek.agents.agents import (
    Agents,
    AgentForm,
    AgentResponse,
    AgentModel,
)
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
from world_seek.config import FASTGPT_BASE_URL, FASTGPT_TOKEN, REQUEST_TIMEOUT, LANGFLOW_BASE_URL, LANGFLOW_API_BASE_URL, LANGFLOW_TOKEN

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)  # 设置为 DEBUG 级别以显示所有日志

# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
log.addHandler(console_handler)

async def sync_workflows_with_database(flows: List[Dict[str, Any]], user):
    """
    将获取到的工作流与数据库中的数据同步
    
    Args:
        flows: 从API获取的工作流列表
        user: 当前用户
    
    Returns:
        None
    """
    log.info(f"开始同步工作流数据到数据库: 工作流数量={len(flows)}")
    
    try:
        # 获取数据库中现有的所有工作流
        existing_workflows = Workflows.get_all_workflows()
        existing_workflow_ids = {w.api_path: w for w in existing_workflows}
        
        # 记录处理结果
        updated_count = 0
        created_count = 0
        unchanged_count = 0
        deleted_count = 0
        
        # 跟踪API返回的工作流ID
        api_flow_ids = set()
        
        # 遍历API返回的工作流
        for flow in flows:
            flow_id = flow.get("id")
            if not flow_id:
                log.warning(f"工作流缺少ID字段，跳过: {flow}")
                continue
            
            api_flow_ids.add(flow_id)
                
            # 准备工作流数据
            try:  
                workflow_data = WorkflowForm(
                    name=flow.get("name", "未命名工作流"),
                    description=flow.get("description", ""),
                    api_path=flow_id,
                )

                log.info(f"创建WorkflowForm: {workflow_data}")
            except Exception as e:
                log.error(f"创建WorkflowForm时出错: {str(e)}, flow_id={flow_id}")
                continue
            
            # 检查工作流是否已存在
            if flow_id in existing_workflow_ids:
                existing_workflow = existing_workflow_ids[flow_id]
                
                # 检查是否需要更新
                needs_update = (
                    existing_workflow.name != workflow_data.name or
                    existing_workflow.description != workflow_data.description
                )
                
                if needs_update:
                    # 更新工作流
                    updated_workflow = Workflows.update_workflow_by_id(existing_workflow.id, workflow_data)
                    if updated_workflow:
                        log.info(f"更新工作流: ID={existing_workflow.id}, 名称={workflow_data.name}")
                        updated_count += 1
                    else:
                        log.error(f"更新工作流失败: ID={existing_workflow.id}")
                else:
                    log.debug(f"工作流无需更新: ID={existing_workflow.id}")
                    unchanged_count += 1
            else:
                # 如果不存在，创建新工作流
                new_workflow = Workflows.insert_new_workflow(workflow_data)
                if new_workflow:
                    log.info(f"创建新工作流: ID={new_workflow.id}, 名称={workflow_data.name}")
                    created_count += 1
                else:
                    log.error(f"创建工作流失败: flow_id={flow_id}")
        
        # 处理需要删除的工作流（数据库中存在但API返回中不存在）
        for db_workflow_id, db_workflow in existing_workflow_ids.items():
            log.info(f"检查工作流: ID={db_workflow.id}, 名称={db_workflow.name}, api_path={db_workflow_id}")
            if db_workflow_id not in api_flow_ids:
                # 删除工作流
                if Workflows.delete_workflow_by_id(db_workflow.id):
                    log.info(f"删除不存在的工作流: ID={db_workflow.id}, 名称={db_workflow.name}, api_path={db_workflow_id}")
                    deleted_count += 1
                else:
                    log.error(f"删除工作流失败: ID={db_workflow.id}")
        
        log.info(f"工作流同步完成: 新增={created_count}, 更新={updated_count}, 无变化={unchanged_count}, 删除={deleted_count}")
    except Exception as e:
        log.error(f"同步工作流数据时发生错误: {str(e)}")
        # 不抛出异常，让API仍然可以返回数据

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
    
    # 先从Langflow API获取最新的工作流数据
    try:
        log.info("从Langflow获取最新工作流数据")
        async with aiohttp.ClientSession() as session:
            url = f"{LANGFLOW_API_BASE_URL}/flows/?remove_example_flows=true&components_only=false&get_all=true&header_flows=false&page=1&size=1000"
            headers = {
                "Authorization": LANGFLOW_TOKEN,
                "accept": "application/json"
            }

            log.info(f"发送请求到Langflow: URL={url}")
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    log.info(f"成功获取Langflow工作流数据: {type(data)}")
                    
                    # 处理不同的数据结构
                    flows_list = []
                    
                    if isinstance(data, list):
                        # 如果data是列表，使用列表
                        flows_list = data
                    elif isinstance(data, dict):
                        # 如果data是字典，尝试获取flows字段
                        flows_list = data.get("flows", [])
                    else:
                        # 如果是其他类型，包装成列表
                        flows_list = [data] if data else []
                    
                    # 筛选掉is_component为true的对象
                    filtered_flows = [flow for flow in flows_list if not flow.get("is_component", False)]
                    
                    log.info(f"过滤前工作流数量: {len(flows_list)}, 过滤后: {len(filtered_flows)}")
                    
                    # 同步数据库中的工作流数据
                    await sync_workflows_with_database(filtered_flows, user)
                else:
                    error_text = await response.text()
                    log.warning(f"Langflow请求失败，将使用现有数据库数据: 状态码={response.status}, 错误信息={error_text}")
    except Exception as e:
        log.warning(f"从Langflow获取工作流数据失败，将使用现有数据库数据: {str(e)}")
    
    # 返回数据库中的工作流数据
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
    # 将用户信息存储在params中
    if form_data.params is None:
        form_data.params = {}
    form_data.params["user_id"] = user.id
    workflow = Workflows.insert_new_workflow(form_data)
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
    agent_id = form_data.get("agent_id")

    log.info(f"执行工作流: 工作流ID={workflow_id}, 智能体ID={agent_id}, 用户ID={user.id}")
    
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
    
    # 获取智能体
    agent = Agents.get_agent_by_id(agent_id)
    if not agent:
        log.warning(f"智能体未找到: ID={agent_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        # 准备API URL
        api_url = LANGFLOW_BASE_URL + workflow.api_path
        if not api_url:
            log.error(f"API路径未配置: ID={workflow_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Langflow API path not configured for this workflow",
            )
        
        log.info(f"完整API URL: {api_url}")
        
        # 获取App Token
        app_token = workflow.app_token
        if not app_token and hasattr(workflow, 'params') and workflow.params:
            app_token = workflow.params.get("app_token")
        
        # 获取参数
        params = form_data.get("params", {})
        stream = params.get("stream", True)
        timeout = params.get("timeout", REQUEST_TIMEOUT)

        # 合并智能体与工作流应用参数
        agent_params = agent.params or {}
        workflow_params = workflow.params or {}
        merged_params = {**workflow_params, **agent_params}
        log.info(f"合并后的参数: {merged_params}")
        
        # 基本的输入值，不包含知识库参数
        input_value = {
            "user_input": latest_message,
        }
        
        # 检查是否有知识库参数
        knowledge_params = merged_params.get("knowledge", {})
        if knowledge_params:
            kb_settings = knowledge_params.get("settings", {})
            kb_items = knowledge_params.get("items", [])
            
            # 只有当知识库项目存在时，才添加知识库参数
            if kb_items:
                dataset_id = kb_items[0]
                input_value["kb_params"] = {
                    "datasetId": dataset_id,
                    "text": latest_message,
                    "searchMode": kb_settings.get("searchMode", "embedding"),
                    "limit": kb_settings.get("limit", 10),
                    "similarity": kb_settings.get("similarity", 0.5),
                    "usingReRank": kb_settings.get("usingReRank", True),
                    "datasetSearchUsingExtensionQuery": kb_settings.get("datasetSearchUsingExtensionQuery", False),
                }
                input_value["url_value"] = FASTGPT_BASE_URL + "/api/core/dataset/searchTest"
                log.info("添加知识库参数到请求")
            else:
                log.info("知识库items为空，不添加知识库参数")
        else:
            log.info("未找到知识库参数，不添加知识库参数")
        
        # 准备请求数据
        langflow_data = {
            "input_value": json.dumps(input_value),
            # "input_value": latest_message,
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


############################
# GetKnowledgeBases
############################

@router.get("/knowledge_bases")
async def get_knowledge_bases(user=Depends(get_verified_user)):
    """
    获取知识库列表
    
    Args:
        user: 当前用户
        
    Returns:
        知识库列表
    """
    log.info(f"开始获取知识库列表: 用户ID={user.id}, 角色={user.role}")
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{FASTGPT_BASE_URL}/api/core/dataset/list?parentId="
            headers = {
                "Authorization": f"Bearer {FASTGPT_TOKEN}",
                "Content-Type": "application/json"
            }
            log.info(f"发送请求到FastGPT: URL={url}")
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    log.info(f"成功获取知识库列表: {data}")
                    log.info(f"成功获取知识库列表: {type(data)}")
                    return JSONResponse(content={"data": data.get("data", [])})
                else:
                    error_text = await response.text()
                    log.error(f"FastGPT请求失败: 状态码={response.status}, 错误信息={error_text}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="获取知识库列表失败"
                    )
    except Exception as e:
        log.error(f"获取知识库列表时发生错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库列表失败: {str(e)}"
        )

