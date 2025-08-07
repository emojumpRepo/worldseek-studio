from typing import Optional

from world_seek.agents.agents import (
    AgentForm,
    AgentModel,
    AgentResponse,
    AgentUserWorkflowResponse,
    Agents,
)
from world_seek.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status


from world_seek.utils.auth import get_admin_user, get_verified_user
from world_seek.utils.access_control import has_access, has_permission


router = APIRouter()


###########################
# GetAgents
###########################


@router.get("/", response_model=list[AgentUserWorkflowResponse])
async def get_agents(id: Optional[str] = None, user=Depends(get_verified_user)):
    print(f"get_agents: {user}")
    if user.role == "admin":
        return Agents.get_agents(user_id=user.id, user_role=user.role)
    else:
        return Agents.get_agents_by_user_id(user.id)


###########################
# GetWorkspaceAgents
###########################


@router.get("/workspace", response_model=list[AgentUserWorkflowResponse])
async def get_workspace_agents(user=Depends(get_verified_user)):
    """
    获取工作空间可展示的智能体列表
    - 仅返回当前用户创建的智能体
    - 适用于所有用户角色，确保数据隔离
    """
    return Agents.get_workspace_agents_by_user_id(user.id)


###########################
# GetBaseAgents
###########################


@router.get("/base", response_model=list[AgentResponse])
async def get_base_agents(user=Depends(get_admin_user)):
    return Agents.get_base_agents()


############################
# CreateNewAgent
############################


@router.post("/create", response_model=Optional[AgentModel])
async def create_new_agent(
    request: Request,
    form_data: AgentForm,
    user=Depends(get_verified_user),
):
    print(f"create_new_agent: {form_data}")
    if user.role != "admin" and not has_permission(
        user.id, "workspace.agents", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    # 检查ID是否已存在
    if form_data.id:
        agent = Agents.get_agent_by_id(form_data.id)
        if agent:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ERROR_MESSAGES.AGENT_ID_TAKEN,
            )

    # 创建新代理
    agent = Agents.insert_new_agent(form_data, user.id)
    if agent:
        return agent
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT("Failed to create agent. Please check logs for details."),
        )


###########################
# GetModelById
###########################


# Note: We're not using the typical url path param here, but instead using a query parameter to allow '/' in the id
@router.get("/agent", response_model=Optional[AgentResponse])
async def get_agent_by_id(id: str, user=Depends(get_verified_user)):
    agent = Agents.get_agent_by_id(id)
    if agent:
        if (
            user.role == "admin"
            or agent.user_id == user.id
            or has_access(user.id, "read", agent.access_control)
        ):
            return agent
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# ToggleAgentById
############################


@router.post("/agent/toggle", response_model=Optional[AgentResponse])
async def toggle_agent_by_id(id: str, user=Depends(get_verified_user)):
    agent = Agents.get_agent_by_id(id)
    if agent:
        if (
            user.role == "admin"
            or agent.user_id == user.id
            or has_access(user.id, "write", agent.access_control)
        ):
            agent = Agents.toggle_agent_by_id(id)

            if agent:
                return agent
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error updating function"),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateAgentById
############################


@router.post("/agent/update", response_model=Optional[AgentModel])
async def update_agent_by_id(
    id: str,
    form_data: AgentForm,
    user=Depends(get_verified_user),
):
    agent = Agents.get_agent_by_id(id)
    print(f"update_agent: {agent}")

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        agent.user_id != user.id
        and not has_access(user.id, "write", agent.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    agent = Agents.update_agent_by_id(id, form_data)
    return agent


############################
# DeleteAgentById
############################


@router.delete("/agent/delete", response_model=bool)
async def delete_agent_by_id(id: str, user=Depends(get_verified_user)):
    agent = Agents.get_agent_by_id(id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role != "admin"
        and agent.user_id != user.id
        and not has_access(user.id, "write", agent.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = Agents.delete_agent_by_id(id)
    return result


@router.delete("/delete/all", response_model=bool)
async def delete_all_agents(user=Depends(get_admin_user)):
    result = Agents.delete_all_agents()
    return result
