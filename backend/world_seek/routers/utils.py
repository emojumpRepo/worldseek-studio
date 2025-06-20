import black
import logging
import markdown

from world_seek.models.chats import ChatTitleMessagesForm
from world_seek.config import DATA_DIR, ENABLE_ADMIN_EXPORT
from world_seek.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from starlette.responses import FileResponse


from world_seek.utils.misc import get_gravatar_url
from world_seek.utils.pdf_generator import PDFGenerator
from world_seek.utils.auth import get_admin_user, get_verified_user
from world_seek.utils.code_interpreter import execute_code_jupyter
from world_seek.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


@router.get("/gravatar")
async def get_gravatar(email: str, user=Depends(get_verified_user)):
    return get_gravatar_url(email)


class CodeForm(BaseModel):
    code: str


@router.post("/code/format")
async def format_code(form_data: CodeForm, user=Depends(get_verified_user)):
    try:
        formatted_code = black.format_str(form_data.code, mode=black.Mode())
        return {"code": formatted_code}
    except black.NothingChanged:
        return {"code": form_data.code}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/code/execute")
async def execute_code(
    request: Request, form_data: CodeForm, user=Depends(get_verified_user)
):
    if request.app.state.config.CODE_EXECUTION_ENGINE == "jupyter":
        output = await execute_code_jupyter(
            request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
            form_data.code,
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == "token"
                else None
            ),
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == "password"
                else None
            ),
            request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        )

        return output
    else:
        raise HTTPException(
            status_code=400,
            detail="Code execution engine not supported",
        )


class MarkdownForm(BaseModel):
    md: str


@router.post("/markdown")
async def get_html_from_markdown(
    form_data: MarkdownForm, user=Depends(get_verified_user)
):
    return {"html": markdown.markdown(form_data.md)}


class ChatForm(BaseModel):
    title: str
    messages: list[dict]


@router.post("/pdf")
async def download_chat_as_pdf(
    form_data: ChatTitleMessagesForm, user=Depends(get_verified_user)
):
    try:
        pdf_bytes = PDFGenerator(form_data).generate_chat_pdf()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment;filename=chat.pdf"},
        )
    except Exception as e:
        log.exception(f"Error generating PDF: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/db/download")
async def download_db(user=Depends(get_admin_user)):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    from world_seek.internal.db import engine

    if engine.name != "sqlite":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DB_NOT_SQLITE,
        )
    return FileResponse(
        engine.url.database,
        media_type="application/octet-stream",
        filename="webui.db",
    )

@router.get("/db/pool-status")
async def get_db_pool_status(user=Depends(get_admin_user)):
    """获取数据库连接池状态"""
    from world_seek.internal.db import engine
    
    if hasattr(engine.pool, 'size'):
        pool_info = {
            "pool_size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "invalid": engine.pool.invalid(),
        }
        
        # 计算使用率
        total_connections = pool_info["checked_in"] + pool_info["checked_out"]
        max_connections = engine.pool._max_overflow + engine.pool._pool_size
        usage_percentage = (total_connections / max_connections * 100) if max_connections > 0 else 0
        
        pool_info.update({
            "total_connections": total_connections,
            "max_connections": max_connections,
            "usage_percentage": round(usage_percentage, 2),
            "status": "healthy" if usage_percentage < 80 else "warning" if usage_percentage < 95 else "critical"
        })
        
        return pool_info
    else:
        return {"message": "连接池信息不可用", "pool_type": str(type(engine.pool))}

@router.post("/db/pool-reset")
async def reset_db_pool(user=Depends(get_admin_user)):
    """重置数据库连接池（谨慎使用）"""
    from world_seek.internal.db import engine
    
    try:
        # 记录重置前的状态
        if hasattr(engine.pool, 'size'):
            before_status = {
                "checked_out": engine.pool.checkedout(),
                "checked_in": engine.pool.checkedin(),
            }
        else:
            before_status = {"message": "无法获取重置前状态"}
        
        # 执行连接池重置
        engine.pool.dispose()
        
        return {
            "message": "数据库连接池已重置",
            "before_status": before_status,
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置连接池失败: {str(e)}"
        )


@router.get("/litellm/config")
async def download_litellm_config_yaml(user=Depends(get_admin_user)):
    return FileResponse(
        f"{DATA_DIR}/litellm/config.yaml",
        media_type="application/octet-stream",
        filename="config.yaml",
    )
