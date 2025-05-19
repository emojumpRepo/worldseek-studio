import logging
import aiohttp
import json
import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, Union, List, Tuple, TypeVar, Callable, Awaitable
from dataclasses import dataclass
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

from world_seek.env import SRC_LOG_LEVELS, AIOHTTP_CLIENT_TIMEOUT, AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION

# 类型定义
T = TypeVar('T')
ResponseType = Union[Dict[str, Any], StreamingResponse]
StreamChunk = Tuple[bytes, bool]

# 日志配置
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("LANGFLOW", SRC_LOG_LEVELS["MAIN"]))

# 常量定义
DEFAULT_TIMEOUT = 120  # 默认超时时间(秒)
MAX_RETRIES = 2  # 最大重试次数
RETRY_BACKOFF_FACTOR = 2  # 重试退避因子
CHUNK_SIZE = 8192  # 数据块大小
LOG_INTERVAL = 1.0  # 日志记录间隔(秒)
MAX_ERROR_LENGTH = 200  # 错误信息最大长度
MAX_CONTENT_LENGTH = 10000  # 内容最大长度

@dataclass
class StreamStats:
    """流式处理统计信息"""
    chunk_count: int = 0
    total_bytes: int = 0
    start_time: float = 0.0
    last_log_time: float = 0.0
    accumulated_content: str = ""

class WorkflowError(Exception):
    """工作流相关错误的基类"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}

class WorkflowTimeoutError(WorkflowError):
    """工作流超时错误"""
    pass

class WorkflowAPIError(WorkflowError):
    """工作流API错误"""
    pass

class WorkflowStreamError(WorkflowError):
    """工作流流式处理错误"""
    pass

@asynccontextmanager
async def create_aiohttp_session(timeout: int) -> AsyncGenerator[aiohttp.ClientSession, None]:
    """创建aiohttp会话的上下文管理器"""
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        yield session

def create_headers(token: str) -> Dict[str, str]:
    """创建请求头"""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if token and token.strip():
        headers["Authorization"] = f"Bearer {token}" if not token.startswith('Bearer ') else token
    return headers

def format_url(base_url: str, path: str) -> str:
    """格式化URL"""
    if path.startswith(('http://', 'https://')):
        return path
    base_url = base_url.rstrip('/')
    path = path.lstrip('/')
    return f"{base_url}/{path}"

def format_stream_url(url: str) -> str:
    """格式化流式URL"""
    if "?" in url:
        return f"{url}&stream=true"
    return f"{url}?stream=true"

async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = MAX_RETRIES,
    backoff_factor: int = RETRY_BACKOFF_FACTOR,
    **kwargs: Any
) -> T:
    """带退避的重试机制"""
    last_exception = None
    for retry in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if retry < max_retries:
                wait_time = backoff_factor ** retry
                log.warning(f"操作失败，{wait_time}秒后重试: {str(e)}")
                await asyncio.sleep(wait_time)
    
    if last_exception:
        raise last_exception
    raise WorkflowError("重试失败")

async def process_response(response: aiohttp.ClientResponse) -> Dict[str, Any]:
    """处理API响应"""
    if not response.ok:
        error_text = await response.text()
        log.error(f"API错误({response.status}): {error_text[:MAX_ERROR_LENGTH]}")
        raise WorkflowAPIError(f"API错误({response.status})", {"details": error_text[:MAX_ERROR_LENGTH]})
    
    content_type = response.headers.get('Content-Type', '')
    if 'html' in content_type.lower() and 'json' not in content_type.lower():
        error_text = await response.text()
        log.warning(f"收到HTML而非JSON: {error_text[:MAX_ERROR_LENGTH]}...")
        raise WorkflowAPIError("收到HTML响应而非JSON", {"content_type": content_type})
    
    try:
        return await response.json()
    except json.JSONDecodeError:
        text_response = await response.text()
        log.error(f"JSON解析失败: {text_response[:MAX_ERROR_LENGTH]}...")
        raise WorkflowAPIError("无法解析JSON响应", {"response": text_response[:MAX_ERROR_LENGTH]})

async def call_langflow_api(
    base_url: str,
    path: str,
    token: str,
    data: Dict[str, Any],
    stream: bool = False,
    timeout: int = DEFAULT_TIMEOUT
) -> ResponseType:
    """
    调用Langflow API
    
    Args:
        base_url: Langflow服务URL
        path: API路径或完整URL
        token: Application Token
        data: 请求数据
        stream: 是否使用流式响应
        timeout: 请求超时时间(秒)
        
    Returns:
        API响应或StreamingResponse
        
    Raises:
        WorkflowTimeoutError: 请求超时
        WorkflowAPIError: API调用失败
    """
    url = format_url(base_url, path)
    log.info(f"Langflow API请求: URL={url}, 流模式={stream}")
    
    if stream:
        stream_url = format_stream_url(url)
        return StreamingResponse(
            langflow_stream_generator(stream_url, token, data, timeout),
            media_type="text/event-stream"
        )
    
    async def make_request() -> Dict[str, Any]:
        async with create_aiohttp_session(timeout) as session:
            headers = create_headers(token)
            async with session.post(url, json=data, headers=headers) as response:
                return await process_response(response)
    
    return await retry_with_backoff(make_request)

async def process_stream_chunk(
    chunk: StreamChunk,
    stats: StreamStats,
    process_json_data: Callable[[Dict[str, Any]], AsyncGenerator[str, None]]
) -> AsyncGenerator[str, None]:
    """处理流式数据块"""
    chunk_data, _ = chunk
    chunk_text = chunk_data.decode('utf-8')
    stats.chunk_count += 1
    stats.total_bytes += len(chunk_data)
    
    try:
        if chunk_text.startswith('data:'):
            json_text = chunk_text.replace('data:', '').strip()
            if json_text == '[DONE]':
                if stats.accumulated_content:
                    yield f"data: {json.dumps({'accumulated_content': stats.accumulated_content})}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            try:
                json_data = json.loads(json_text)
                async for chunk in process_json_data(json_data):
                    yield chunk
            except json.JSONDecodeError:
                log.warning(f"无法解析JSON: {json_text}")
        else:
            try:
                json_data = json.loads(chunk_text)
                async for chunk in process_json_data(json_data):
                    yield chunk
            except json.JSONDecodeError:
                yield f"data: {json.dumps({'content': chunk_text})}\n\n"
                stats.accumulated_content += chunk_text
    except Exception as e:
        log.error(f"处理数据块错误: {e}")

async def langflow_stream_generator(
    url: str,
    token: str,
    data: Dict[str, Any],
    timeout: int
) -> AsyncGenerator[str, None]:
    """
    生成Langflow流式响应的异步生成器
    
    Args:
        url: Langflow API URL
        token: Authorization token
        data: 请求数据
        timeout: 请求超时时间(秒)
        
    Yields:
        流式响应的数据块
        
    Raises:
        WorkflowError: 流式处理过程中的错误
    """
    stats = StreamStats(start_time=time.time(), last_log_time=time.time())
    
    try:
        log.info(f"初始化Langflow流式请求: URL={url}")
        headers = create_headers(token)
        
        async with create_aiohttp_session(timeout) as session:
            try:
                async with session.post(url, json=data, headers=headers) as response:
                    if not response.ok:
                        error_text = await response.text()
                        log.error(f"Langflow API流式错误: {error_text}")
                        error_data = {"error": {"detail": error_text}}
                        yield f"data: {json.dumps(error_data)}\n\n"
                        return
                    
                    async def process_json_data(json_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
                        """处理JSON数据并生成响应"""
                        if 'data' in json_data and 'result' in json_data['data']:
                            result = json_data['data']['result']
                            if 'outputs' in result and result['outputs']:
                                for output in result['outputs']:
                                    if 'outputs' in output and output['outputs']:
                                        for inner_output in output['outputs']:
                                            if 'outputs' in inner_output and 'message' in inner_output['outputs']:
                                                message = inner_output['outputs']['message']
                                                if 'message' in message:
                                                    content = message['message']
                                                    if content:
                                                        yield f"data: {json.dumps({'content': content})}\n\n"
                                                        stats.accumulated_content += content
                        elif json_data.get('event') == 'token' and 'data' in json_data and 'chunk' in json_data['data']:
                            token_content = json_data['data']['chunk']
                            if token_content:
                                token_event = {
                                    "event": "token",
                                    "data": {
                                        "chunk": token_content,
                                        "id": json_data['data'].get('id', str(uuid.uuid4())),
                                        "timestamp": json_data['data'].get('timestamp', datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
                                    }
                                }
                                yield f"data: {json.dumps(token_event, ensure_ascii=False)}\n\n"
                                stats.accumulated_content += token_content
                    
                    async for chunk in response.content.iter_chunks():
                        if chunk:
                            current_time = time.time()
                            
                            async for processed_chunk in process_stream_chunk(chunk, stats, process_json_data):
                                yield processed_chunk
                            
                            if current_time - stats.last_log_time >= LOG_INTERVAL:
                                log.info(f"流式进度: {stats.chunk_count}块, {stats.total_bytes}字节")
                                stats.last_log_time = current_time
                    
                    if stats.accumulated_content:
                        complete_response = {
                            "id": "langflow-complete",
                            "complete": True,
                            "content": stats.accumulated_content
                        }
                        yield f"data: {json.dumps(complete_response)}\n\n"
                    
                    yield "data: [DONE]\n\n"
                    
                    stream_duration = time.time() - stats.start_time
                    log.info(f"Langflow流式请求完成: 总耗时={stream_duration:.2f}秒, 总数据块={stats.chunk_count}, 总大小={stats.total_bytes}字节")
                    
            except asyncio.TimeoutError:
                timeout_duration = time.time() - stats.start_time
                log.warning(f"Langflow流式请求超时: 已执行={timeout_duration:.2f}秒")
                error_data = {"error": {"detail": f"工作流执行超时。执行时间超过 {timeout} 秒。"}}
                yield f"data: {json.dumps(error_data)}\n\n"
    
    except Exception as e:
        error_time = time.time()
        if hasattr(stats, 'start_time'):
            error_duration = error_time - stats.start_time
            log.error(f"Langflow流式生成器错误: {e}, 已执行时间={error_duration:.2f}秒")
        else:
            log.error(f"Langflow流式生成器错误: {e}")
        
        error_data = {"error": {"detail": str(e)}}
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"

async def handleLangflowStream(res: Any, responseMessage: Any) -> None:
    """
    处理Langflow流式响应
    
    Args:
        res: 响应对象
        responseMessage: 响应消息对象
    """
    if not res or not res.body:
        log.error('Invalid response from Langflow streaming API')
        return

    reader = res.body.getReader()
    decoder = TextDecoder('utf-8')
    accumulatedContent = responseMessage.content or ''
    receivedCompleteResponse = False
    
    try:
        while True:
            result = await reader.read()
            if result.done:
                break
                
            chunk = decoder.decode(result.value)
            lines = chunk.split('\n')
            
            for line in lines:
                if not line.startswith('data:'):
                    continue
                    
                data = line[5:].strip()
                if data == '[DONE]':
                    continue

                try:
                    jsonData = json.loads(data)
                    
                    if jsonData.get('error'):
                        log.error('Langflow stream error:', jsonData['error'])
                        responseMessage.error = {
                            'content': jsonData['error'].get('detail', 'Error in Langflow stream')
                        }
                        continue
                    
                    if jsonData.get('id') == 'langflow-complete' and jsonData.get('complete') is True:
                        if jsonData.get('content'):
                            accumulatedContent = jsonData['content']
                            responseMessage.content = accumulatedContent
                            receivedCompleteResponse = True
                        continue

                    messageContent = extract_message_content(jsonData)
                    if messageContent:
                        accumulatedContent += messageContent
                        responseMessage.content = accumulatedContent
                        await asyncio.sleep(0)

                except json.JSONDecodeError as e:
                    log.error(f'Error parsing JSON from stream: {e}')
                except Exception as e:
                    log.error(f'Error processing stream data: {e}')
                    
    except Exception as error:
        log.error(f'Error reading stream: {error}')
        responseMessage.error = {
            'content': f'Stream error: {str(error)}'
        }
    finally:
        responseMessage.content = accumulatedContent
        responseMessage.done = True
        
        if receivedCompleteResponse:
            log.info('流式响应完成，使用后端提供的完整内容')
        else:
            log.info('流式响应完成，使用前端累积的内容')

def extract_message_content(jsonData: Dict[str, Any]) -> str:
    """从JSON数据中提取消息内容"""
    if jsonData.get('outputs') and isinstance(jsonData['outputs'], list):
        for output in jsonData['outputs']:
            if output.get('outputs') and isinstance(output['outputs'], list):
                for inner_output in output['outputs']:
                    if inner_output.get('results', {}).get('message', {}).get('text'):
                        return inner_output['results']['message']['text']
    elif jsonData.get('choices') and jsonData['choices'][0].get('delta', {}).get('content'):
        return jsonData['choices'][0]['delta']['content']
    elif jsonData.get('text'):
        return jsonData['text']
    elif jsonData.get('response'):
        return jsonData['response']
    return ""
