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
