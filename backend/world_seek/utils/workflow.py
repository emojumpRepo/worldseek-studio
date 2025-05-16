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

# 增加超时设置的默认值，以秒为单位
DEFAULT_TIMEOUT = 120  # 默认超时设置为120秒
MAX_RETRIES = 2  # 最大重试次数

async def call_langflow_api(base_url: str, path: str, token: str, data: Dict[str, Any], stream: bool = False, timeout: int = DEFAULT_TIMEOUT) -> Any:
    """
    调用Langflow API
    
    Args:
        base_url: Langflow服务URL
        path: API路径或完整URL
        token: Application Token (可选)
        data: 请求数据
        stream: 是否使用流式响应
        timeout: 请求超时时间(秒)
        
    Returns:
        API响应或StreamingResponse
    """
    # 使用提供的path作为完整URL，如果它看起来像一个完整的URL
    if path.startswith(('http://', 'https://')):
        url = path
    else:
        # 否则，构建URL
        base_url = base_url.rstrip('/')
        path = path.lstrip('/')
        url = f"{base_url}/{path}"
    
    log.info(f"Langflow API请求: URL={url}, 流模式={stream}, 超时={timeout}秒")
    
    if stream:
        # 返回StreamingResponse以支持流式输出
        stream_url = url
        if "?" not in url:
            stream_url = f"{url}?stream=true"
        elif not url.endswith("stream=true"):
            stream_url = f"{url}&stream=true"
            
        return StreamingResponse(
            langflow_stream_generator(stream_url, '', data, timeout),
            media_type="text/event-stream"
        )
    
    # 非流式请求
    retry_count = 0
    last_exception = None
    
    while retry_count <= MAX_RETRIES:
        try:
            request_start_time = time.time()
            
            # 使用指定的超时设置
            aiohttp_timeout = aiohttp.ClientTimeout(total=timeout)
            
            # 简化的请求头
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # 只有在提供了token且token不为空时才添加Authorization头
            if token and token.strip():
                if not token.startswith('Bearer '):
                    headers["Authorization"] = f"Bearer {token}"
                else:
                    headers["Authorization"] = token
            
            log.debug(f"请求头: {headers}")
            log.debug(f"请求数据: {data}")
            
            async with aiohttp.ClientSession(timeout=aiohttp_timeout) as session:
                log.info(f"发送请求: 第{retry_count+1}次尝试")
                
                async with session.post(url, json=data, headers=headers) as response:
                    response_time = time.time() - request_start_time
                    log.info(f"接收到响应: 状态码={response.status}, 耗时={response_time:.2f}秒")
                    
                    # 处理错误状态码
                    if response.status >= 400:
                        error_text = await response.text()
                        log.error(f"API错误({response.status}): {error_text}")
                        raise Exception(f"API错误({response.status}): {error_text[:200]}")
                    
                    # 检查内容类型
                    content_type = response.headers.get('Content-Type', '')
                    if 'html' in content_type.lower() and 'json' not in content_type.lower():
                        error_text = await response.text()
                        log.warning(f"收到HTML而非JSON: {error_text[:200]}...")
                        raise Exception("收到HTML响应而非JSON，可能是CDN错误")
                    
                    # 解析JSON响应
                    try:
                        response_data = await response.json()
                        log.info(f"成功解析JSON响应: 大小={len(str(response_data))}字节")
                        
                        # 记录截断的响应数据
                        response_str = str(response_data)
                        log_content = response_str[:500] + "..." if len(response_str) > 500 else response_str
                        log.debug(f"响应内容: {log_content}")
                        
                        return response_data
                    except json.JSONDecodeError:
                        text_response = await response.text()
                        log.error(f"JSON解析失败: {text_response[:200]}...")
                        raise Exception(f"无法解析JSON响应: {text_response[:100]}...")
            
        except asyncio.TimeoutError:
            timeout_duration = time.time() - request_start_time
            log.warning(f"请求超时: 已耗时={timeout_duration:.2f}秒, 超时设置={timeout}秒, 尝试次数={retry_count+1}/{MAX_RETRIES+1}")
            last_exception = Exception(f"请求超时。已尝试{retry_count+1}次，总耗时{timeout_duration:.2f}秒")
        
        except Exception as e:
            error_duration = time.time() - request_start_time if 'request_start_time' in locals() else 0
            log.error(f"请求失败: {str(e)}, 耗时={error_duration:.2f}秒, 尝试次数={retry_count+1}/{MAX_RETRIES+1}")
            last_exception = e
        
        # 增加重试次数
        retry_count += 1
        
        if retry_count <= MAX_RETRIES:
            # 等待时间随重试次数增加 (1, 2, 4, 8...秒)
            wait_time = 2 ** (retry_count - 1)
            log.info(f"等待{wait_time}秒后重试...")
            await asyncio.sleep(wait_time)
    
    # 所有重试都失败
    if last_exception:
        raise last_exception
    else:
        raise Exception("请求失败，所有重试均未成功")

async def langflow_stream_generator(url: str, token: str, data: Dict[str, Any], timeout: int) -> AsyncGenerator[str, None]:
    """
    生成Langflow流式响应的异步生成器
    
    Args:
        url: Langflow API URL
        token: Authorization token
        data: 请求数据
        timeout: 请求超时时间(秒)
        
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
        # if token:
        #     if token.startswith('Bearer '):
        #         headers["Authorization"] = token
        #     else:
        #         headers["Authorization"] = f"Bearer {token}"
        
        log.info(f"流式请求头: {headers}")
        
        stream_start_time = time.time()
        log.info(f"开始Langflow流式请求: 时间={stream_start_time}")
        
        # 使用工具执行超时值替代一般超时
        aiohttp_timeout = aiohttp.ClientTimeout(total=timeout)
        log.info(f"流式请求超时设置: {timeout}秒")
        
        chunk_count = 0
        total_bytes = 0
        last_chunk_time = stream_start_time
        
        # 添加累积内容变量
        accumulated_content = ""
        
        async with aiohttp.ClientSession(timeout=aiohttp_timeout) as session:
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
                    timeout=timeout
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
                            
                            # 记录数据块内容 (每50个块详细记录一次，其他时候仅记录简短内容)
                            if chunk_count % 50 == 1:  # 1, 51, 101...
                                # 详细记录，但仍然截断过长内容
                                log_text = chunk_text[:500] + "..." if len(chunk_text) > 500 else chunk_text
                                log.debug(f"流式数据块[{chunk_count}]内容: {log_text}")
                            
                            # 检查流格式，有些情况下Langflow可能会直接返回SSE格式
                            if chunk_text.startswith('data:'):
                                # 记录SSE格式数据
                                if chunk_count % 20 == 1:
                                    log_data = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                                    log.debug(f"接收SSE格式数据[{chunk_count}]: {log_data}")
                                
                                # 尝试提取和累积内容
                                try:
                                    data_content = chunk_text.split('data:')[1].strip()
                                    if data_content and data_content != '[DONE]':
                                        json_data = json.loads(data_content)
                                        if 'choices' in json_data and json_data['choices'][0].get('delta', {}).get('content'):
                                            accumulated_content += json_data['choices'][0]['delta']['content']
                                except Exception as e:
                                    log.debug(f"从SSE提取内容失败: {e}")
                                
                                yield chunk_text + '\n'
                            else:
                                try:
                                    # 尝试解析JSON
                                    parsed_data = json.loads(chunk_text)
                                    # 记录解析后的JSON数据
                                    if chunk_count % 20 == 1:
                                        response_content = parsed_data.get("response", "")
                                        log_response = response_content[:200] + "..." if len(response_content) > 200 else response_content
                                        log.debug(f"解析JSON数据块[{chunk_count}]: response={log_response}")
                                    
                                    # 累积内容
                                    if "response" in parsed_data:
                                        accumulated_content += parsed_data.get("response", "")
                                    
                                    # 转换为OpenAI兼容的格式
                                    formatted_data = {
                                        "id": "langflow",
                                        "choices": [{
                                            "delta": {
                                                "content": parsed_data.get("response", "")
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
                    
                    # 记录会话总结
                    average_chunk_size = total_bytes / chunk_count if chunk_count > 0 else 0
                    chunks_per_second = chunk_count / stream_duration if stream_duration > 0 else 0
                    log.info(f"Langflow流式会话总结: 平均块大小={average_chunk_size:.2f}字节, 平均速率={chunks_per_second:.2f}块/秒")
                    
                    # 发送完整响应内容
                    log.info(f"发送完整累积内容, 大小={len(accumulated_content)}字节")
                    complete_response = {
                        "id": "langflow-complete",
                        "complete": True,
                        "content": accumulated_content
                    }
                    yield f"data: {json.dumps(complete_response)}\n\n"
                    
                    # 发送结束标记
                    yield "data: [DONE]\n\n"
            except asyncio.TimeoutError:
                timeout_time = time.time()
                timeout_duration = timeout_time - stream_start_time
                log.warning(f"Langflow流式请求超时: 已执行={timeout_duration:.2f}秒, 超时设置={timeout}秒, 已接收={chunk_count}块")
                error_data = {"error": {"detail": f"工作流执行超时。执行时间超过 {timeout} 秒，请尝试简化操作或联系管理员调整超时设置。"}}
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
