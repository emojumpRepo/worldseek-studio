import logging
import aiohttp
import json
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi.responses import StreamingResponse
import time

from world_seek.env import SRC_LOG_LEVELS, AIOHTTP_CLIENT_TIMEOUT, AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("LANGFLOW", SRC_LOG_LEVELS["MAIN"]))

async def call_langflow_api(base_url: str, path: str, token: str, data: Dict[str, Any], stream: bool = False) -> Any:
    """
    调用Langflow API
    
    Args:
        base_url: Langflow服务URL
        path: API路径
        token: Application Token
        data: 请求数据
        stream: 是否使用流式响应
        
    Returns:
        API响应或StreamingResponse
    """
    # 规范化URL路径
    base_url = base_url.rstrip('/')
    path = path.lstrip('/')
    
    # 检查path是否是完整URL，如果是，直接使用
    if path.startswith('http://') or path.startswith('https://'):
        url = path
    else:
        url = f"{base_url}/{path}"
    
    log.debug(f"Calling Langflow API: {url}, stream={stream}")
    
    # 记录请求的详细信息
    log.info(f"Langflow API请求详情: URL={url}, 流模式={stream}, 数据大小={len(str(data))}字节")
    log.info(f"Langflow数据类型: input_type={data.get('input_type')}, output_type={data.get('output_type')}")
    
    # 检查token格式
    if token and not token.startswith('Bearer '):
        log.info("Token不是Bearer格式，添加Bearer前缀")
        auth_header = f"Bearer {token}"
    else:
        auth_header = token
    
    if stream:
        # 返回StreamingResponse以支持流式输出
        log.info(f"初始化Langflow流式响应: URL={url}")
        url = url + "?stream=true"
        return StreamingResponse(
            langflow_stream_generator(url, auth_header, data),
            media_type="text/event-stream"
        )
    
    try:
        # 使用工具执行超时设置，确保Langflow API响应不会无限等待
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION)
        log.info(f"使用超时设置: {AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION}秒")
        
        request_start_time = time.time()
        log.info(f"开始Langflow API请求: 时间={request_start_time}")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 添加认证头
        if auth_header:
            if auth_header.startswith('Bearer '):
                headers["Authorization"] = auth_header
            else:
                headers["Authorization"] = f"Bearer {auth_header}"
        
        log.info(f"请求头: {headers}")
        
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            try:
                # 添加asyncio.wait_for超时控制
                log.debug(f"发送POST请求: URL={url}")
                session_start_time = time.time()
                
                # 尝试发送请求
                async with await asyncio.wait_for(
                    session.post(
                        url,
                        json=data,
                        headers=headers
                    ),
                    timeout=AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION
                ) as response:
                    session_end_time = time.time()
                    session_duration = session_end_time - session_start_time
                    log.info(f"收到Langflow API响应: 状态码={response.status}, 耗时={session_duration:.2f}秒")
                    
                    # 处理不同的状态码
                    if response.status == 403:
                        error_text = await response.text()
                        log.error(f"Langflow API请求被拒绝(403): {error_text}")
                        raise Exception(f"API请求被拒绝(403 Forbidden)，可能是认证问题或API限制: {error_text}")
                    elif response.status == 404:
                        error_text = await response.text()
                        log.error(f"Langflow API端点不存在(404): {error_text}")
                        raise Exception(f"API端点不存在(404 Not Found): {url}")
                    elif response.status >= 400:
                        error_text = await response.text()
                        log.error(f"Langflow API错误({response.status}): {error_text}")
                        raise Exception(f"API错误({response.status}): {error_text}")
                    
                    # 如果响应是HTML而非JSON，可能是CloudFront错误页面
                    content_type = response.headers.get('Content-Type', '')
                    if 'html' in content_type.lower():
                        error_text = await response.text()
                        log.error(f"收到HTML响应而非JSON: {error_text[:200]}...")
                        raise Exception(f"收到非预期的HTML响应，可能是CDN错误: {error_text[:200]}...")
                    
                    # 正常解析JSON响应
                    json_start_time = time.time()
                    try:
                        response_data = await response.json()
                    except:
                        # 如果无法解析JSON，记录原始响应
                        text_response = await response.text()
                        log.error(f"无法解析JSON响应: {text_response[:500]}...")
                        raise Exception(f"无法解析JSON响应: {text_response[:200]}...")
                    
                    json_end_time = time.time()
                    json_duration = json_end_time - json_start_time
                    
                    log.info(f"解析JSON响应: 耗时={json_duration:.2f}秒, 响应大小={len(str(response_data))}字节")
                    
                    if not response.ok:
                        log.error(f"Langflow API错误: {response_data}")
                        raise Exception(response_data.get("detail", "Unknown error"))
                    
                    request_end_time = time.time()
                    total_request_duration = request_end_time - request_start_time
                    log.info(f"完成Langflow API请求: 总耗时={total_request_duration:.2f}秒")
                    
                    return response_data
            except asyncio.TimeoutError:
                timeout_time = time.time()
                timeout_duration = timeout_time - request_start_time
                log.warning(f"Langflow API超时: 已执行={timeout_duration:.2f}秒, 超时设置={AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION}秒")
                raise Exception(f"工作流执行超时。执行时间超过 {AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION} 秒，请尝试简化操作或联系管理员调整超时设置。")
    except aiohttp.ClientError as e:
        error_time = time.time()
        if 'request_start_time' in locals():
            error_duration = error_time - request_start_time
            log.error(f"Langflow API连接错误: {e}, 已执行时间={error_duration:.2f}秒")
        else:
            log.error(f"Langflow API连接错误: {e}")
        raise Exception(f"Connection error: {e}")
    except Exception as e:
        error_time = time.time()
        if 'request_start_time' in locals():
            error_duration = error_time - request_start_time
            log.error(f"Langflow API未预期错误: {e}, 已执行时间={error_duration:.2f}秒")
        else:
            log.error(f"Langflow API未预期错误: {e}")
        raise

async def langflow_stream_generator(url: str, token: str, data: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    生成Langflow流式响应的异步生成器
    
    Args:
        url: Langflow API URL
        token: Authorization token
        data: 请求数据
        
    Yields:
        流式响应的数据块
    """
    try:
        # 添加stream=true参数到URL
        if "?" in url:
            stream_url = f"{url}&stream=true"
        else:
            stream_url = f"{url}?stream=true"
            
        log.debug(f"Streaming from Langflow API: {stream_url}")
        log.info(f"初始化Langflow流式请求: URL={stream_url}, 数据大小={len(str(data))}字节")
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "WorldSeek-Studio/1.0",
            "Accept": "application/json"
        }
        
        # 添加认证头
        if token:
            if token.startswith('Bearer '):
                headers["Authorization"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
        
        log.info(f"流式请求头: {headers}")
        
        stream_start_time = time.time()
        log.info(f"开始Langflow流式请求: 时间={stream_start_time}")
        
        # 使用工具执行超时值替代一般超时
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION)
        log.info(f"流式请求超时设置: {AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION}秒")
        
        chunk_count = 0
        total_bytes = 0
        last_chunk_time = stream_start_time
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # 添加asyncio.wait_for超时控制
                session_start = time.time()
                log.debug(f"发送流式POST请求: URL={stream_url}")
                
                async with await asyncio.wait_for(
                    session.post(
                        stream_url,
                        json=data,
                        headers=headers
                    ),
                    timeout=AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION
                ) as response:
                    session_end = time.time()
                    session_duration = session_end - session_start
                    log.info(f"收到Langflow流式连接: 状态码={response.status}, 耗时={session_duration:.2f}秒")
                    
                    if not response.ok:
                        error_text = await response.text()
                        log.error(f"Langflow API流式错误: {error_text}")
                        error_data = {"error": {"detail": error_text}}
                        yield f"data: {json.dumps(error_data)}\n\n"
                        return
                    
                    # 处理流式响应
                    log.info(f"开始接收Langflow流式数据块")
                    async for chunk in response.content:
                        current_time = time.time()
                        chunk_interval = current_time - last_chunk_time
                        last_chunk_time = current_time
                        
                        if chunk:
                            chunk_count += 1
                            chunk_size = len(chunk)
                            total_bytes += chunk_size
                            
                            # 每10个块记录一次详细信息，避免日志过多
                            if chunk_count % 10 == 0:
                                elapsed = current_time - stream_start_time
                                log.info(f"流式数据统计: 已接收={chunk_count}块, 总大小={total_bytes}字节, 已用时间={elapsed:.2f}秒, 块间隔={chunk_interval:.3f}秒")
                            
                            # 将Langflow流式响应转换为标准SSE格式
                            chunk_text = chunk.decode('utf-8')
                            # 检查流格式，有些情况下Langflow可能会直接返回SSE格式
                            if chunk_text.startswith('data:'):
                                yield chunk_text + '\n'
                            else:
                                try:
                                    # 尝试解析JSON
                                    data = json.loads(chunk_text)
                                    # 转换为OpenAI兼容的格式
                                    formatted_data = {
                                        "id": "langflow",
                                        "choices": [{
                                            "delta": {
                                                "content": data.get("response", "")
                                            },
                                            "index": 0
                                        }]
                                    }
                                    yield f"data: {json.dumps(formatted_data)}\n\n"
                                except json.JSONDecodeError:
                                    # 非JSON格式，直接作为内容传递
                                    yield f"data: {json.dumps({'text': chunk_text})}\n\n"
                    
                    # 流结束
                    stream_end_time = time.time()
                    stream_duration = stream_end_time - stream_start_time
                    log.info(f"Langflow流式请求完成: 总耗时={stream_duration:.2f}秒, 总数据块={chunk_count}, 总大小={total_bytes}字节")
                    yield "data: [DONE]\n\n"
            except asyncio.TimeoutError:
                timeout_time = time.time()
                timeout_duration = timeout_time - stream_start_time
                log.warning(f"Langflow流式请求超时: 已执行={timeout_duration:.2f}秒, 超时设置={AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION}秒, 已接收={chunk_count}块")
                error_data = {"error": {"detail": f"工作流执行超时。执行时间超过 {AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION} 秒，请尝试简化操作或联系管理员调整超时设置。"}}
                yield f"data: {json.dumps(error_data)}\n\n"
    
    except Exception as e:
        error_time = time.time()
        if 'stream_start_time' in locals():
            error_duration = error_time - stream_start_time
            log.error(f"Langflow流式生成器错误: {e}, 已执行时间={error_duration:.2f}秒")
        else:
            log.error(f"Langflow流式生成器错误: {e}")
            
        error_data = {"error": {"detail": str(e)}}
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"
