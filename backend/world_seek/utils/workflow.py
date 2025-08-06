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
    session_id: Optional[str] = None

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
        headers["x-api-key"] = token
    log.info(f"请求头: {headers}")
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
    
    # 增加原始数据块日志输出
    log.info(f"[DEBUG] 收到原始数据块 #{stats.chunk_count}: {chunk_text[:500]}{'...' if len(chunk_text) > 500 else ''}")
    
    try:
        if chunk_text.startswith('data:'):
            json_text = chunk_text.replace('data:', '').strip()
            log.info(f"[DEBUG] 提取的JSON文本: {json_text[:300]}{'...' if len(json_text) > 300 else ''}")
            
            if json_text == '[DONE]':
                log.info("[DEBUG] 收到流结束标记 [DONE]")
                if stats.accumulated_content:
                    yield f"data: {json.dumps({'accumulated_content': stats.accumulated_content})}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            try:
                json_data = json.loads(json_text)
                log.info(f"[DEBUG] 解析的JSON数据: {json.dumps(json_data, ensure_ascii=False, indent=2)[:800]}{'...' if len(str(json_data)) > 800 else ''}")
                async for chunk in process_json_data(json_data):
                    log.info(f"[DEBUG] 生成的响应块: {chunk[:200]}{'...' if len(chunk) > 200 else ''}")
                    yield chunk
            except json.JSONDecodeError:
                log.warning(f"无法解析JSON: {json_text}")
                error_data = {"error": {"detail": "数据格式解析失败，请稍后重试或联系管理员"}}
                yield f"data: {json.dumps(error_data)}\n\n"
        else:
            log.info(f"[DEBUG] 非data:格式的数据块: {chunk_text[:300]}{'...' if len(chunk_text) > 300 else ''}")
            try:
                json_data = json.loads(chunk_text)
                log.info(f"[DEBUG] 直接解析的JSON数据: {json.dumps(json_data, ensure_ascii=False, indent=2)[:800]}{'...' if len(str(json_data)) > 800 else ''}")
                
                # 处理 Langflow 的特殊事件格式
                if json_data.get('event') == 'token' and 'data' in json_data and 'chunk' in json_data['data']:
                    # 处理 token 事件
                    token_content = json_data['data']['chunk']
                    log.info(f"[DEBUG] 处理token事件，内容: {token_content}")
                    if token_content:
                        stats.accumulated_content += token_content
                        yield f"data: {json.dumps({'content': token_content})}\n\n"
                elif json_data.get('event') == 'end' and 'data' in json_data and 'result' in json_data['data']:
                    # 处理 end 事件
                    result = json_data['data']['result']
                    log.info(f"[DEBUG] 处理end事件，result: {result}")
                    
                    # # 保存 session_id
                    # if 'session_id' in json_data['data']['result']:
                    #     stats.session_id = json_data['data']['result']['session_id']
                    #     log.info(f"[DEBUG] 保存session_id: {stats.session_id}")
                    
                    # 尝试从复杂的数据结构中提取最终内容
                    final_content = None
                    
                    # 方法1: 直接从result中提取message
                    if 'message' in result:
                        final_content = result['message']
                        log.info(f"[DEBUG] 从result.message获取最终消息: {final_content[:100]}{'...' if len(final_content) > 100 else ''}")
                    
                    # 方法2: 从outputs结构中提取内容
                    elif 'outputs' in result and result['outputs']:
                        for output in result['outputs']:
                            if 'outputs' in output and output['outputs']:
                                for inner_output in output['outputs']:
                                    if 'results' in inner_output and 'message' in inner_output['results']:
                                        message = inner_output['results']['message']
                                        if 'data' in message and 'text' in message['data']:
                                            final_content = message['data']['text']
                                            log.info(f"[DEBUG] 从outputs结构获取最终消息: {final_content[:100]}{'...' if len(final_content) > 100 else ''}")
                                            break
                                if final_content:
                                    break
                    
                    if final_content:
                        # 使用最终完整消息替换累积内容
                        stats.accumulated_content = final_content
                        
                        # 构建 langflow-complete 事件，包含 session_id
                        complete_data = {
                            'id': 'langflow-complete',
                            'complete': True,
                            'content': final_content
                        }
                        if stats.session_id:
                            complete_data['session_id'] = stats.session_id
                            log.info(f"[DEBUG] 在完成事件中包含session_id: {stats.session_id}")
                            
                        yield f"data: {json.dumps(complete_data)}\n\n"
                    else:
                        log.warning("[DEBUG] 无法从end事件中提取内容")
                elif json_data.get('event') == 'add_message':
                    # 处理 add_message 事件（可能包含初始消息信息）
                    log.info(f"[DEBUG] 处理add_message事件")
                    # 这类事件通常不包含内容，只是消息元数据，可以忽略或记录
                elif json_data.get('event') == 'end' and 'data' in json_data and 'result' in json_data['data']:
                    # 处理 end 事件，提取最终文本内容
                    result = json_data['data']['result']
                    final_content = None
                    
                    # 尝试从复杂的数据结构中提取最终内容
                    if 'outputs' in result and result['outputs']:
                        for output in result['outputs']:
                            if 'outputs' in output and output['outputs']:
                                for inner_output in output['outputs']:
                                    if 'results' in inner_output and 'message' in inner_output['results']:
                                        message = inner_output['results']['message']
                                        if 'data' in message and 'text' in message['data']:
                                            final_content = message['data']['text']
                                            log.info(f"[DEBUG] 从end事件提取最终内容: {final_content[:100]}{'...' if len(final_content) > 100 else ''}")
                                            break
                                if final_content:
                                    break
                    
                    if final_content:
                        # 只返回纯文本内容，不返回JSON结构
                        yield f"data: {final_content}\n\n"
                        stats.accumulated_content = final_content
                else:
                    # 使用原有的处理逻辑处理其他格式
                    async for chunk in process_json_data(json_data):
                        log.info(f"[DEBUG] 生成的响应块: {chunk[:200]}{'...' if len(chunk) > 200 else ''}")
                        yield chunk
                        
            except json.JSONDecodeError:
                log.info(f"[DEBUG] 无法解析为JSON，作为纯文本处理: {chunk_text[:200]}{'...' if len(chunk_text) > 200 else ''}")
                # 检查是否是空行或只包含空白字符
                if chunk_text.strip():
                    # 只有真正有内容的文本才处理
                    yield f"data: {json.dumps({'content': chunk_text})}\n\n"
                    stats.accumulated_content += chunk_text
                # 移除空数据的错误报告，因为空行在流式响应中是正常的
                
    except Exception as e:
        log.error(f"处理数据块错误: {e}")
        error_data = {"error": {"detail": f"数据处理异常: {str(e)[:100]}，请联系管理员"}}
        yield f"data: {json.dumps(error_data)}\n\n"

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
        log.info(f"[DEBUG] 请求数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}{'...' if len(str(data)) > 500 else ''}")
        headers = create_headers(token)
        log.info(f"[DEBUG] 请求头: {headers}")
        
        async with create_aiohttp_session(timeout) as session:
            try:
                async with session.post(url, json=data, headers=headers) as response:
                    log.info(f"[DEBUG] HTTP响应状态: {response.status}")
                    log.info(f"[DEBUG] HTTP响应头: {dict(response.headers)}")
                    
                    if not response.ok:
                        error_text = await response.text()
                        log.error(f"Langflow API流式错误: {error_text}")
                        # 根据HTTP状态码提供更友好的错误信息
                        if response.status == 401:
                            error_msg = "身份验证失败，请检查API密钥是否正确"
                        elif response.status == 403:
                            error_msg = "访问被拒绝，请检查权限配置"
                        elif response.status == 404:
                            error_msg = "工作流不存在，请检查URL和流程ID是否正确"
                        elif response.status == 500:
                            error_msg = "服务器内部错误，请稍后重试或联系管理员"
                        elif response.status == 503:
                            error_msg = "服务暂时不可用，请稍后重试"
                        else:
                            error_msg = f"请求失败(状态码: {response.status})，请联系管理员"
                        
                        error_data = {"error": {"detail": error_msg}}
                        yield f"data: {json.dumps(error_data)}\n\n"
                        return
                    
                    async def process_json_data(json_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
                        """处理JSON数据并生成响应"""
                        log.info(f"[DEBUG] 开始处理JSON数据，结构: {list(json_data.keys())}")
                        
                        if 'data' in json_data and 'result' in json_data['data']:
                            log.info(f"[DEBUG] 发现标准数据结构，result keys: {list(json_data['data']['result'].keys())}")
                            result = json_data['data']['result']
                            if 'outputs' in result and result['outputs']:
                                log.info(f"[DEBUG] 找到outputs，数量: {len(result['outputs'])}")
                                for i, output in enumerate(result['outputs']):
                                    log.info(f"[DEBUG] 处理output #{i}: {list(output.keys())}")
                                    if 'outputs' in output and output['outputs']:
                                        for j, inner_output in enumerate(output['outputs']):
                                            log.info(f"[DEBUG] 处理inner_output #{j}: {list(inner_output.keys())}")
                                            # 尝试从不同的结构中提取内容
                                            content = None
                                            
                                            # 方法1: 从outputs.message中提取
                                            if 'outputs' in inner_output and 'message' in inner_output['outputs']:
                                                message = inner_output['outputs']['message']
                                                log.info(f"[DEBUG] 找到message: {list(message.keys())}")
                                                if 'message' in message:
                                                    content = message['message']
                                            
                                            # 方法2: 从results.message.data.text中提取
                                            elif 'results' in inner_output and 'message' in inner_output['results']:
                                                message = inner_output['results']['message']
                                                if 'data' in message and 'text' in message['data']:
                                                    content = message['data']['text']
                                            
                                            if content:
                                                log.info(f"[DEBUG] 提取到内容: {content[:100]}{'...' if len(content) > 100 else ''}")
                                                yield f"data: {json.dumps({'content': content})}\n\n"
                                                stats.accumulated_content += content
                        elif json_data.get('event') == 'token' and 'data' in json_data and 'chunk' in json_data['data']:
                            token_content = json_data['data']['chunk']
                            log.info(f"[DEBUG] 发现token事件，内容: {token_content[:100]}{'...' if len(token_content) > 100 else ''}")
                            if token_content:
                                token_event = {
                                    "event": "token",
                                    "data": {
                                        "chunk": token_content,
                                        "id": json_data['data'].get('id', str(uuid.uuid4())),
                                        "timestamp": json_data['data'].get('timestamp', datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
                                    }
                                }
                                log.info(f"[DEBUG] 生成token事件: {json.dumps(token_event, ensure_ascii=False)[:200]}{'...' if len(str(token_event)) > 200 else ''}")
                                yield f"data: {json.dumps(token_event, ensure_ascii=False)}\n\n"
                                stats.accumulated_content += token_content
                        else:
                            log.info(f"[DEBUG] 未识别的JSON数据格式，完整数据: {json.dumps(json_data, ensure_ascii=False, indent=2)[:500]}{'...' if len(str(json_data)) > 500 else ''}")
                    
                    try:
                        chunk_processed = False
                        async for chunk in response.content.iter_chunks():
                            if chunk:
                                chunk_processed = True
                                current_time = time.time()
                                
                                try:
                                    async for processed_chunk in process_stream_chunk(chunk, stats, process_json_data):
                                        yield processed_chunk
                                except Exception as chunk_error:
                                    log.error(f"处理数据块时发生错误: {chunk_error}")
                                    error_data = {"error": {"detail": f"数据流处理异常，请稍后重试"}}
                                    yield f"data: {json.dumps(error_data)}\n\n"
                                
                                if current_time - stats.last_log_time >= LOG_INTERVAL:
                                    log.info(f"流式进度: {stats.chunk_count}块, {stats.total_bytes}字节")
                                    stats.last_log_time = current_time
                        
                        # 检查是否处理了任何数据块
                        if not chunk_processed:
                            log.warning("[DEBUG] 没有收到任何数据块")
                            error_data = {"error": {"detail": "服务器未返回任何数据，请检查工作流配置"}}
                            yield f"data: {json.dumps(error_data)}\n\n"
                            
                    except Exception as stream_error:
                        log.error(f"流式数据读取错误: {stream_error}")
                        error_data = {"error": {"detail": "数据流读取异常，请检查网络连接或稍后重试"}}
                        yield f"data: {json.dumps(error_data)}\n\n"
                    
                    if stats.accumulated_content:
                        log.info(f"[DEBUG] 最终累积内容长度: {len(stats.accumulated_content)} 字符")
                        log.info(f"[DEBUG] 最终累积内容前500字符: {stats.accumulated_content[:500]}{'...' if len(stats.accumulated_content) > 500 else ''}")
                        complete_response = {
                            "id": "langflow-complete",
                            "complete": True,
                            "content": stats.accumulated_content,
                            "session_id": stats.session_id
                        }
                        yield f"data: {json.dumps(complete_response)}\n\n"
                    else:
                        log.warning("[DEBUG] 没有累积到任何内容")
                        error_data = {"error": {"detail": "智能体回答内容为空，请稍后重试"}}
                        yield f"data: {json.dumps(error_data)}\n\n"
                    
                    yield "data: [DONE]\n\n"
                    
                    stream_duration = time.time() - stats.start_time
                    log.info(f"Langflow流式请求完成: 总耗时={stream_duration:.2f}秒, 总数据块={stats.chunk_count}, 总大小={stats.total_bytes}字节")
                    log.info(f"[DEBUG] 完整流式响应统计: 数据块={stats.chunk_count}, 字节数={stats.total_bytes}, 累积内容长度={len(stats.accumulated_content)}")
                    
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
        
        # 根据错误类型提供更友好的错误信息
        error_str = str(e).lower()
        if "connection" in error_str or "network" in error_str:
            error_msg = "网络连接异常，请检查网络连接或稍后重试"
        elif "timeout" in error_str:
            error_msg = "请求超时，请稍后重试或联系管理员"
        elif "ssl" in error_str or "certificate" in error_str:
            error_msg = "SSL证书验证失败，请检查网络配置"
        elif "permission" in error_str or "access" in error_str:
            error_msg = "访问权限异常，请检查配置或联系管理员"
        else:
            error_msg = f"系统异常，请联系管理员 (错误: {str(e)[:50]})"
        
        error_data = {"error": {"detail": error_msg}}
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
        responseMessage.error = {
            'content': '无效的流式响应，请检查服务配置或联系管理员'
        }
        responseMessage.done = True
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
                    log.info(f"[DEBUG] 跳过非data行: {line[:100]}{'...' if len(line) > 100 else ''}")
                    continue
                    
                data = line[5:].strip()
                log.info(f"[DEBUG] 处理data行: {data[:200]}{'...' if len(data) > 200 else ''}")
                
                if data == '[DONE]':
                    log.info("[DEBUG] 在handleLangflowStream中收到 [DONE]")
                    continue

                try:
                    jsonData = json.loads(data)
                    log.info(f"[DEBUG] handleLangflowStream解析JSON: {json.dumps(jsonData, ensure_ascii=False, indent=2)[:300]}{'...' if len(str(jsonData)) > 300 else ''}")
                    
                    if jsonData.get('error'):
                        log.error('Langflow stream error:', jsonData['error'])
                        responseMessage.error = {
                            'content': jsonData['error'].get('detail', 'Error in Langflow stream')
                        }
                        continue
                    
                    if jsonData.get('id') == 'langflow-complete' and jsonData.get('complete') is True:
                        log.info("[DEBUG] 收到完整响应事件")
                        if jsonData.get('content'):
                            accumulatedContent = jsonData['content']
                            responseMessage.content = accumulatedContent
                            receivedCompleteResponse = True
                            log.info(f"[DEBUG] 设置完整内容，长度: {len(accumulatedContent)}")
                        continue

                    messageContent = extract_message_content(jsonData)
                    log.info(f"[DEBUG] 提取的消息内容: {messageContent[:100]}{'...' if messageContent and len(messageContent) > 100 else ''}")
                    if messageContent:
                        accumulatedContent += messageContent
                        responseMessage.content = accumulatedContent
                        log.info(f"[DEBUG] 累积内容更新，当前长度: {len(accumulatedContent)}")
                        await asyncio.sleep(0)

                except json.JSONDecodeError as e:
                    log.error(f'Error parsing JSON from stream: {e}')
                    responseMessage.error = {
                        'content': '数据格式错误，请稍后重试或联系管理员'
                    }
                except Exception as e:
                    log.error(f'Error processing stream data: {e}')
                    responseMessage.error = {
                        'content': f'数据处理异常，请联系管理员'
                    }
                    
    except Exception as error:
        log.error(f'Error reading stream: {error}')
        # 根据错误类型提供友好的错误信息
        error_str = str(error).lower()
        if "connection" in error_str or "network" in error_str:
            error_msg = "网络连接中断，请检查网络或稍后重试"
        elif "timeout" in error_str:
            error_msg = "响应超时，请稍后重试"
        elif "closed" in error_str:
            error_msg = "连接已关闭，请重新发起请求"
        else:
            error_msg = "流式数据读取异常，请联系管理员"
        
        responseMessage.error = {
            'content': error_msg
        }
    finally:
        # 确保响应消息始终有内容，即使出现错误
        if not hasattr(responseMessage, 'error') or not responseMessage.error:
            responseMessage.content = accumulatedContent or ""
            
            # 如果没有任何内容且没有错误，设置默认错误
            if not responseMessage.content and not hasattr(responseMessage, 'error'):
                responseMessage.error = {
                    'content': '未收到任何响应内容，请稍后重试或联系管理员'
                }
        
        responseMessage.done = True
        
        if receivedCompleteResponse:
            log.info('流式响应完成，使用后端提供的完整内容')
        elif accumulatedContent:
            log.info('流式响应完成，使用前端累积的内容')
        else:
            log.warning('流式响应完成，但没有累积到任何有效内容')

def extract_message_content(jsonData: Dict[str, Any]) -> str:
    """从JSON数据中提取消息内容"""
    log.info(f"[DEBUG] extract_message_content 输入数据结构: {list(jsonData.keys())}")
    
    if jsonData.get('outputs') and isinstance(jsonData['outputs'], list):
        log.info(f"[DEBUG] 找到outputs数组，长度: {len(jsonData['outputs'])}")
        for i, output in enumerate(jsonData['outputs']):
            log.info(f"[DEBUG] 处理output #{i}: {list(output.keys())}")
            if output.get('outputs') and isinstance(output['outputs'], list):
                for j, inner_output in enumerate(output['outputs']):
                    log.info(f"[DEBUG] 处理inner_output #{j}: {list(inner_output.keys())}")
                    if inner_output.get('results', {}).get('message', {}).get('text'):
                        content = inner_output['results']['message']['text']
                        log.info(f"[DEBUG] 从outputs路径提取内容: {content[:100]}{'...' if len(content) > 100 else ''}")
                        return content
    elif jsonData.get('choices') and jsonData['choices'][0].get('delta', {}).get('content'):
        content = jsonData['choices'][0]['delta']['content']
        log.info(f"[DEBUG] 从choices路径提取内容: {content[:100]}{'...' if len(content) > 100 else ''}")
        return content
    elif jsonData.get('text'):
        content = jsonData['text']
        log.info(f"[DEBUG] 从text字段提取内容: {content[:100]}{'...' if len(content) > 100 else ''}")
        return content
    elif jsonData.get('response'):
        content = jsonData['response']
        log.info(f"[DEBUG] 从response字段提取内容: {content[:100]}{'...' if len(content) > 100 else ''}")
        return content
    
    log.info("[DEBUG] 没有找到可提取的消息内容")
    return ""
