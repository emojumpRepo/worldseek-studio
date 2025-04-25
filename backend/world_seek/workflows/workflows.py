import logging
import time
from typing import Optional

from world_seek.internal.db import Base, JSONField, get_db
from world_seek.env import SRC_LOG_LEVELS

from world_seek.models.users import Users, UserResponse


from pydantic import BaseModel, ConfigDict

from sqlalchemy import or_, and_, func
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy import BigInteger, Column, Text, JSON, Boolean, Integer


from world_seek.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AGENTS"])


####################
# Workflow DB Schema
####################


# WorkflowParams is a model for the data stored in the params field of the Workflow table
class WorkflowParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    pass


class Workflow(Base):
    __tablename__ = "workflow_app"

    id = Column(Integer, primary_key=True)
    """
        The workflow's id as used in the API. If set to an existing workflow, it will override the workflow.
    """
    name = Column(Text)
    """
        The human-readable display name of the model.
    """

    description = Column(Text)
    """
        The description of the agent.
    """

    params = Column(JSONField)
    """
        Holds a JSON encoded blob of parameters, see `ModelParams`.
    """

    is_deleted = Column(Boolean, default=False)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class WorkflowModel(BaseModel):
    id: int
    
    name: str
    description: str
    params: Optional[dict] = None

    is_deleted: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################

class WorkflowResponse(WorkflowModel):
    pass


class WorkflowForm(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    is_deleted: bool = False
    params: Optional[dict] = None

class ModelsTable:
    def insert_new_workflow(
        self, form_data: WorkflowForm
    ) -> Optional[WorkflowModel]:
        model = WorkflowModel(
            **{
                **form_data.model_dump(),
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
        )
        try:
            with get_db() as db:
                result = Workflow(**model.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)

                if result:
                    return WorkflowModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            log.exception(f"Failed to insert a new workflow: {e}")
            return None

    def get_all_workflows(self) -> list[WorkflowModel]:
        with get_db() as db:
            return [WorkflowModel.model_validate(model) for model in db.query(Workflow).all()]

    def get_workflows(self, user_id: str = None, user_role: str = None) -> list[WorkflowResponse]:
        try:
            with get_db() as db:
                workflows = []
                # 获取所有记录
                all_workflows = db.query(Workflow).all()
                print(f"查询到 {len(all_workflows)} 条记录")
                
                for workflow in all_workflows:
                    try:
                        print(f"处理workflow: {workflow.id}")

                        # 安全地验证模型
                        try:
                            workflow_model = WorkflowModel.model_validate(workflow)
                            workflow_data = workflow_model.model_dump()
                            
                            # 构建响应对象
                            response_data = {
                                **workflow_data,
                            }
                            
                            workflow_response = WorkflowResponse.model_validate(response_data)
                            workflows.append(workflow_response)
                            
                        except Exception as workflow_err:
                            print(f"应用验证失败: {workflow_err}")
                            # 继续处理下一条记录
                    
                    except Exception as workflow_err:
                        print(f"处理单个workflow时出错: {workflow_err}")
                        # 继续处理下一条记录
                
                print(f"成功处理 {len(workflows)} 条记录")
                return workflows
                
        except Exception as e:
            print(f"get_workflows方法发生异常: {e}")
            # 返回空列表而不是抛出异常
            return []

    def get_base_workflows(self) -> list[WorkflowModel]:
        with get_db() as db:
            return [
                WorkflowModel.model_validate(workflow)
                for workflow in db.query(Workflow).filter(Workflow.base_app_id == None).all()
            ]

    def get_workflow_by_id(self, id: str) -> Optional[WorkflowModel]:
        try:
            with get_db() as db:
                workflow = db.get(Workflow, id)
                return WorkflowModel.model_validate(workflow)
        except Exception:
            return None

    def toggle_workflow_by_id(self, id: str) -> Optional[WorkflowModel]:
        with get_db() as db:
            try:
                is_deleted = db.query(Workflow).filter_by(id=id).first().is_deleted

                db.query(Workflow).filter_by(id=id).update(
                    {
                        "is_deleted": not is_deleted,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()

                return self.get_workflow_by_id(id)
            except Exception:
                return None

    def update_workflow_by_id(self, id: str, workflow: WorkflowForm) -> Optional[WorkflowModel]:
        try:
            with get_db() as db:
                # update only the fields that are present in the model
                update_data = workflow.model_dump(exclude={"id", "user_id", "created_at"})
                update_data["updated_at"] = int(time.time())  # 添加更新时间
                
                result = (
                    db.query(Workflow)
                    .filter_by(id=id)
                    .update(update_data)
                )
                db.commit()

                print(f"update_workflow_by_id result: {result}")
                workflow = db.get(Workflow, id)
                db.refresh(workflow)
                return WorkflowModel.model_validate(workflow)
        except Exception as e:
            log.exception(f"Failed to update the workflow by id {id}: {e}")
            return None

    def delete_workflow_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Workflow).filter_by(id=id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_all_models(self) -> bool:
        try:
            with get_db() as db:
                db.query(Workflow).delete()
                db.commit()

                return True
        except Exception:
            return False


Workflows = ModelsTable()
