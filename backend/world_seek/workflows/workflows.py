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
    
    langflow_url: Optional[str] = None
    api_path: Optional[str] = "http://8.130.43.71:7860/api/v1/run/daf471a8-cb78-4d0f-b0b7-8ad75a012652"
    workflow_data: Optional[dict] = None
    # 其他参数
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

    app_token = Column(Text)
    """
        The app token of the workflow.
    """

    api_path = Column(Text)
    """
        The api path of the workflow.
    """

    is_deleted = Column(Boolean, default=False)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class WorkflowModel(BaseModel):
    id: int
    
    name: str
    description: str
    params: Optional[dict] = None
    api_path: Optional[str] = ""
    app_token: Optional[str] = ""

    is_deleted: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def model_validate_workflow(cls, obj, *args, **kwargs):
        """
        自定义模型验证方法，确保api_path和app_token字段被正确设置
        """
        try:
            # 首先使用标准验证
            validated_data = cls.model_validate(obj, *args, **kwargs)
            
            # 安全地处理params字段
            if validated_data.params is None:
                validated_data.params = {}
            elif isinstance(validated_data.params, str):
                try:
                    import json
                    validated_data.params = json.loads(validated_data.params)
                except json.JSONDecodeError:
                    validated_data.params = {}
            
            # 检查api_path是否存在，如果不存在，尝试从params中获取
            if not validated_data.api_path and validated_data.params and isinstance(validated_data.params, dict):
                validated_data.api_path = validated_data.params.get('api_path', "")
            
            return validated_data
        except Exception as e:
            print(f"模型验证失败: {str(e)}")
            # 如果验证失败，返回一个基本的有效对象
            return cls(
                id=obj.id if hasattr(obj, 'id') else 0,
                name=obj.name if hasattr(obj, 'name') else "",
                description=obj.description if hasattr(obj, 'description') else "",
                params={},
                api_path="",
                app_token="",
                is_deleted=obj.is_deleted if hasattr(obj, 'is_deleted') else False,
                updated_at=obj.updated_at if hasattr(obj, 'updated_at') else int(time.time()),
                created_at=obj.created_at if hasattr(obj, 'created_at') else int(time.time())
            )


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
    api_path: Optional[str] = ""
    app_token: Optional[str] = ""

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
                    return WorkflowModel.model_validate_workflow(result)
                else:
                    return None
        except Exception as e:
            log.exception(f"Failed to insert a new workflow: {e}")
            return None

    def get_all_workflows(self) -> list[WorkflowModel]:
        with get_db() as db:
            return [WorkflowModel.model_validate_workflow(model) for model in db.query(Workflow).all()]

    def get_workflows(self, user_id: str = None, user_role: str = None) -> list[WorkflowResponse]:
        try:
            with get_db() as db:
                workflows = []
                all_workflows = db.query(Workflow).all()
                
                for workflow in all_workflows:
                    try:
                        print(f"处理workflow: {workflow.id}")
                        
                        # 安全地处理params字段
                        params = {}
                        if workflow.params is not None:
                            if isinstance(workflow.params, str):
                                try:
                                    import json
                                    params = json.loads(workflow.params)
                                except json.JSONDecodeError:
                                    print(f"JSON解析失败，使用空字典: {workflow.params}")
                                    params = {}
                            elif isinstance(workflow.params, dict):
                                params = workflow.params
                        
                        # 创建基本数据字典
                        workflow_data = {
                            "id": workflow.id,
                            "name": workflow.name or "",
                            "description": workflow.description or "",
                            "params": params,
                            "api_path": workflow.api_path or "",
                            "app_token": workflow.app_token or "",
                            "is_deleted": workflow.is_deleted or False,
                            "updated_at": workflow.updated_at or int(time.time()),
                            "created_at": workflow.created_at or int(time.time())
                        }
                        
                        try:
                            # 验证并创建响应对象
                            workflow_response = WorkflowResponse.model_validate(workflow_data)
                            workflows.append(workflow_response)
                        except Exception as workflow_err:
                            print(f"响应对象验证失败: {workflow_err}")
                            print(f"workflow数据: {workflow_data}")
                            continue
                    
                    except Exception as workflow_err:
                        print(f"处理单个workflow时出错: {workflow_err}")
                        continue
                
                print(f"成功处理 {len(workflows)} 条记录")
                return workflows
                
        except Exception as e:
            print(f"get_workflows方法发生异常: {e}")
            return []

    def get_workflow_by_id(self, id: str) -> Optional[WorkflowModel]:
        try:
            with get_db() as db:
                workflow = db.get(Workflow, id)
                if not workflow:
                    return None
                    
                # 创建工作流模型对象
                workflow_model = WorkflowModel.model_validate_workflow(workflow)
                
                return workflow_model
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
                return WorkflowModel.model_validate_workflow(workflow)
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
