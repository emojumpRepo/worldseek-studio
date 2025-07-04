import logging
import time
from typing import Optional, Union

from world_seek.internal.db import Base, JSONField, get_db
from world_seek.env import SRC_LOG_LEVELS

from world_seek.models.users import Users, UserResponse
from world_seek.workflows.workflows import Workflows, WorkflowResponse

from pydantic import BaseModel, ConfigDict

from sqlalchemy import or_, and_, func
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy import BigInteger, Column, Text, JSON, Boolean, Integer


from world_seek.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AGENTS"])


####################
# Agents DB Schema
####################

class Agent(Base):
    __tablename__ = "agent"

    id = Column(Integer, primary_key=True)
    """
        The agent's id as used in the API. If set to an existing agent, it will override the agent.
    """

    user_id = Column(Text)

    base_app_id = Column(Integer)
    """
        An optional pointer to the actual app that should be used when proxying requests.
    """

    name = Column(Text)
    """
        The human-readable display name of the model.
    """

    description = Column(Text)
    """
        The description of the agent.
    """

    access_control = Column(JSON, nullable=True)  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }

    is_deleted = Column(Boolean, default=False)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class AgentModel(BaseModel):
    id: Optional[int] = None
    base_app_id: Optional[int] = None
    user_id: Optional[str] = None
    
    name: str
    description: str
    access_control: Optional[dict] = None

    is_deleted: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class AgentUserResponse(AgentModel):
    user: Optional[UserResponse] = None

class AgentUserWorkflowResponse(AgentModel):
    user: Optional[UserResponse] = None
    workflow_app: Optional[WorkflowResponse] = None

class AgentResponse(AgentModel):
    pass


class AgentForm(BaseModel):
    id: Optional[Union[int, str]] = None
    base_app_id: Optional[Union[int, str]] = None
    name: str
    description: str
    access_control: Optional[dict] = None
    is_deleted: bool = False
    user_id: Optional[str] = None

class ModelsTable:
    def insert_new_agent(
        self, form_data: AgentForm, user_id: str
    ) -> Optional[AgentModel]:
        print(f"insert_new_agent: {form_data}")
        print(f"user_id: {user_id}")
        try:
            # 确保id字段为整数类型
            form_data_dict = form_data.model_dump()
            if form_data_dict.get('id') and isinstance(form_data_dict['id'], str):
                try:
                    form_data_dict['id'] = int(form_data_dict['id'])
                except ValueError:
                    log.error(f"Failed to convert id to integer: {form_data_dict['id']}")
                    return None
                    
            # 确保base_app_id字段为整数类型或None
            if form_data_dict.get('base_app_id') and isinstance(form_data_dict['base_app_id'], str):
                try:
                    if form_data_dict['base_app_id'] and form_data_dict['base_app_id'].strip():
                        form_data_dict['base_app_id'] = int(form_data_dict['base_app_id'])
                    else:
                        form_data_dict['base_app_id'] = None
                except ValueError:
                    log.error(f"Failed to convert base_app_id to integer: {form_data_dict['base_app_id']}")
                    form_data_dict['base_app_id'] = None
            
            # 移除AgentModel不需要的字段
            if 'parent_agent_id' in form_data_dict:
                del form_data_dict['parent_agent_id']
                
            model = AgentModel(
                **{
                    **form_data_dict,
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            
            with get_db() as db:
                log.debug(f"Creating Agent with data: {model.model_dump()}")
                result = Agent(**model.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)

                print(f"insert_new_agent result: {result}")

                if result:
                    return AgentModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            log.exception(f"Failed to insert a new agent: {e}")
            return None

    def get_all_models(self) -> list[AgentModel]:
        with get_db() as db:
            return [AgentModel.model_validate(model) for model in db.query(Agent).all()]

    def get_agents(self, user_id=None, user_role=None) -> list[AgentUserWorkflowResponse]:
        try:
            with get_db() as db:
                agents = []
                # 获取所有记录，过滤is_deleted=False
                all_agents = db.query(Agent).filter_by(is_deleted=False).all()
                print(f"查询到 {len(all_agents)} 条记录")
                
                for agent in all_agents:
                    try:
                        print(f"处理agent: {agent.id}, user_id: {agent.user_id}")
                        
                        # 安全地获取用户信息
                        user = None
                        if agent.user_id:
                            try:
                                user = Users.get_user_by_id(agent.user_id)
                            except Exception as e:
                                print(f"获取用户信息失败: {e}")
                        
                        # 安全地获取workflow_app
                        workflow_app = None
                        if agent.base_app_id:
                            try:
                                workflow_app = Workflows.get_workflow_by_id(agent.base_app_id)
                            except Exception as e:
                                print(f"获取workflow_app失败: {e}")
                        
                        print(f"workflow_app: {workflow_app}")

                        # 安全地验证模型
                        try:
                            agent_model = AgentModel.model_validate(agent)
                            agent_data = agent_model.model_dump()
                            
                            # 构建响应对象
                            user_data = user.model_dump() if user else None
                            response_data = {
                                **agent_data,
                                "user": user_data,
                                "workflow_app": workflow_app,
                            }
                            
                            agent_response = AgentUserWorkflowResponse.model_validate(response_data)
                            
                            # 如果提供了用户ID和角色，进行权限过滤
                            if user_id is not None:
                                # 如果用户是admin，无需过滤
                                if user_role == "admin":
                                    agents.append(agent_response)
                                # 如果是创建者，允许访问
                                elif agent.user_id == user_id:
                                    agents.append(agent_response)
                                # 当access_control为{}时，只有创建者可以访问（已在上面处理）
                                elif agent.access_control == {}:
                                    continue
                                # 检查是否有访问权限
                                elif has_access(user_id, "read", agent.access_control):
                                    agents.append(agent_response)
                            else:
                                # 如果没有提供用户信息，返回所有代理
                                agents.append(agent_response)
                            
                        except Exception as model_err:
                            print(f"模型验证失败: {model_err}")
                            # 继续处理下一条记录
                    
                    except Exception as agent_err:
                        print(f"处理单个agent时出错: {agent_err}")
                        # 继续处理下一条记录
                
                print(f"成功处理 {len(agents)} 条记录")
                return agents
                
        except Exception as e:
            print(f"get_agents方法发生异常: {e}")
            # 返回空列表而不是抛出异常
            return []

    def get_base_agents(self) -> list[AgentModel]:
        with get_db() as db:
            return [
                AgentModel.model_validate(agent)
                for agent in db.query(Agent).filter(Agent.base_app_id == None).filter_by(is_deleted=False).all()
            ]

    def get_agents_by_user_id(
        self, user_id: str, permission: str = "read", user_role: str = "user"
    ) -> list[AgentUserWorkflowResponse]:
        try:
            agents = []
            with get_db() as db:
                all_agents = db.query(Agent).filter_by(is_deleted=False).all()
                
                for agent in all_agents:
                    try:
                        print(f"处理agent: {agent.id}, access_control: {agent.access_control}")
                        # 如果用户是admin，可以访问所有代理
                        if user_role == "admin":
                            pass  # 跳过权限检查，继续处理
                        # 如果access_control为{}，只有创建者可以访问
                        elif agent.access_control == {} and agent.user_id != user_id:
                            continue
                        # 如果用户不是创建者且没有权限，则跳过
                        elif agent.user_id != user_id and not has_access(user_id, permission, agent.access_control):
                            continue
                        
                        # 到这里，用户要么是admin，要么是创建者，要么有权限访问
                        user = None
                        if agent.user_id:
                            try:
                                user = Users.get_user_by_id(agent.user_id)
                            except Exception as e:
                                print(f"获取用户信息失败: {e}")
                        
                        workflow_app = None
                        if agent.base_app_id:
                            try:
                                workflow_app = Workflows.get_workflow_by_id(agent.base_app_id)
                            except Exception as e:
                                print(f"获取workflow_app失败: {e}")
                        
                        agent_model = AgentModel.model_validate(agent)
                        agent_data = agent_model.model_dump()
                        user_data = user.model_dump() if user else None
                        response_data = {
                            **agent_data,
                            "user": user_data,
                            "workflow_app": workflow_app,
                        }
                        agent_response = AgentUserWorkflowResponse.model_validate(response_data)
                        agents.append(agent_response)
                    except Exception as e:
                        print(f"过滤agent时出错: {e}")
                        continue
            
            return agents
        except Exception as e:
            print(f"get_agents_by_user_id方法发生异常: {e}")
            return []

    def get_agent_by_id(self, id: str) -> Optional[AgentModel]:
        try:
            with get_db() as db:
                agent = db.get(Agent, id)
                if agent and not agent.is_deleted:
                    return AgentModel.model_validate(agent)
                return None
        except Exception:
            return None

    def toggle_agent_by_id(self, id: str) -> Optional[AgentModel]:
        with get_db() as db:
            try:
                is_deleted = db.query(Agent).filter_by(id=id).first().is_deleted

                db.query(Agent).filter_by(id=id).update(
                    {
                        "is_deleted": not is_deleted,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()

                return self.get_agent_by_id(id)
            except Exception:
                return None

    def update_agent_by_id(self, id: str, agent: AgentForm) -> Optional[AgentModel]:
        try:
            with get_db() as db:
                # update only the fields that are present in the model
                update_data = agent.model_dump(exclude={"id", "user_id", "created_at"})
                update_data["updated_at"] = int(time.time())  # 添加更新时间
                
                result = (
                    db.query(Agent)
                    .filter_by(id=id)
                    .update(update_data)
                )
                db.commit()

                print(f"update_agent_by_id result: {result}")
                agent = db.get(Agent, id)
                db.refresh(agent)
                return AgentModel.model_validate(agent)
        except Exception as e:
            log.exception(f"Failed to update the agent by id {id}: {e}")
            return None

    def delete_agent_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Agent).filter_by(id=id).update({"is_deleted": True})
                db.commit()

                return True
        except Exception:
            return False

    def delete_all_models(self) -> bool:
        try:
            with get_db() as db:
                db.query(Agent).delete()
                db.commit()

                return True
        except Exception:
            return False


Agents = ModelsTable()
