import logging
import aiohttp
import json
import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, Union, List
from fastapi.responses import StreamingResponse

from world_seek.env import SRC_LOG_LEVELS, AIOHTTP_CLIENT_TIMEOUT, AIOHTTP_CLIENT_TIMEOUT_TOOL_EXECUTION

# 配置日志
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("LANGFLOW", SRC_LOG_LEVELS["MAIN"]))

# 常量定义
DEFAULT_TIMEOUT = 120  # 默认超时时间(秒)
MAX_RETRIES = 2  # 最大重试次数
STREAM_CHUNK_SIZE = 1024  # 流式响应块大小

# 类型定义
class LangflowResponse:
    def __init__(self, content: str = "", error: Optional[Dict] = None, task_id: Optional[str] = None):
        self.content = content
        self.error = error
        self.task_id = task_id

async def call_langflow_api(
    base_url: str,
    path: str,
    token: str,
    data: Dict[str, Any],
    stream: bool = False,
    timeout: int = DEFAULT_TIMEOUT
) -> Union[Dict[str, Any], StreamingResponse]:
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
    """
    url = path if path.startswith(('http://', 'https://')) else f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    
    log.info(f"Langflow API请求: URL={url}, 流模式={stream}, 超时={timeout}秒")
    
    if stream:
        stream_url = f"{url}{'&' if '?' in url else '?'}stream=true"
        return StreamingResponse(
            langflow_stream_generator(stream_url, token, data, timeout),
            media_type="text/event-stream"
        )
    
    retry_count = 0
    last_exception = None
    
    while retry_count <= MAX_RETRIES:
        try:
            request_start_time = time.time()
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if token and token.strip():
                headers["Authorization"] = f"Bearer {token}" if not token.startswith('Bearer ') else token
            
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.post(url, json=data, headers=headers) as response:
                    response_time = time.time() - request_start_time
                    log.info(f"API响应: 状态码={response.status}, 耗时={response_time:.2f}秒")
                    
                    if response.status >= 400:
                        error_text = await response.text()
                        log.error(f"API错误({response.status}): {error_text[:200]}")
                        raise Exception(f"API错误({response.status}): {error_text[:200]}")
                    
                    content_type = response.headers.get('Content-Type', '')
                    if 'html' in content_type.lower() and 'json' not in content_type.lower():
                        error_text = await response.text()
                        log.warning(f"收到HTML而非JSON: {error_text[:200]}...")
                        raise Exception("收到HTML响应而非JSON，可能是CDN错误")
                    
                    try:
                        response_data = await response.json()
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
        
        retry_count += 1
        
        if retry_count <= MAX_RETRIES:
            wait_time = 2 ** (retry_count - 1)
            log.info(f"等待{wait_time}秒后重试...")
            await asyncio.sleep(wait_time)
    
    if last_exception:
        raise last_exception
    else:
        raise Exception("请求失败，所有重试均未成功")

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
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token}" if not token.startswith('Bearer ') else token
        
        stream_start_time = time.time()
        log.info(f"开始Langflow流式请求: URL={url}")
        
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        accumulated_content = ""
        
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(url, json=data, headers=headers) as response:
                if not response.ok:
                    error_text = await response.text()
                    log.error(f"Langflow API流式错误: {error_text}")
                    error_data = {"error": {"detail": error_text}}
                    yield f"data: {json.dumps(error_data)}\n\n"
                    return
                
                async for chunk in response.content.iter_chunks():
                    if not chunk[0]:
                        continue
                        
                    chunk_text = chunk[0].decode('utf-8')
                    
                    try:
                        if chunk_text.startswith('data:'):
                            json_text = chunk_text.replace('data:', '').strip()
                            
                            if json_text == '[DONE]':
                                if accumulated_content:
                                    yield f"data: {json.dumps({'accumulated_content': accumulated_content})}\n\n"
                                yield "data: [DONE]\n\n"
                                continue
                            
                            try:
                                json_data = json.loads(json_text)
                                
                                if json_data.get('error'):
                                    log.error(f"Langflow stream error: {json_data['error']}")
                                    yield f"data: {json.dumps({'error': json_data['error']})}\n\n"
                                    continue
                                
                                if json_data.get('event') == 'token' and json_data.get('data'):
                                    token_content = json_data['data'].get('chunk', '')
                                    if token_content:
                                        accumulated_content += token_content
                                        yield f"data: {json.dumps({'content': token_content})}\n\n"
                                    continue
                                
                                if json_data.get('id') == 'langflow-complete' and json_data.get('complete'):
                                    if json_data.get('content'):
                                        accumulated_content = json_data['content']
                                        yield f"data: {json.dumps({'content': accumulated_content})}\n\n"
                                    continue
                                
                                message_content = (
                                    json_data.get('content') or
                                    json_data.get('choices', [{}])[0].get('delta', {}).get('content') or
                                    json_data.get('text') or
                                    json_data.get('response') or
                                    ''
                                )
                                
                                if message_content:
                                    accumulated_content += message_content
                                    yield f"data: {json.dumps({'content': message_content})}\n\n"
                                    
                            except json.JSONDecodeError:
                                log.warning(f"无法解析JSON: {json_text[:200]}")
                                yield f"data: {json.dumps({'content': chunk_text})}\n\n"
                                accumulated_content += chunk_text
                                
                    except Exception as e:
                        log.error(f"处理数据块错误: {e}, 原始内容: {chunk_text[:200]}")
                
                if accumulated_content:
                    complete_response = {
                        "id": "langflow-complete",
                        "complete": True,
                        "content": accumulated_content
                    }
                    yield f"data: {json.dumps(complete_response)}\n\n"
                
                yield "data: [DONE]\n\n"
                
                stream_duration = time.time() - stream_start_time
                log.info(f"Langflow流式请求完成: 总耗时={stream_duration:.2f}秒, 累积内容长度={len(accumulated_content)}")
                
    except asyncio.TimeoutError:
        timeout_duration = time.time() - stream_start_time
        log.warning(f"Langflow流式请求超时: 已执行={timeout_duration:.2f}秒, 超时设置={timeout}秒")
        error_data = {"error": {"detail": f"工作流执行超时。执行时间超过 {timeout} 秒。"}}
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

async def handleLangflowStream(res, responseMessage) -> None:
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
                    
                    if jsonData.get('id') == 'langflow-complete' and jsonData.get('complete'):
                        if jsonData.get('content'):
                            accumulatedContent = jsonData['content']
                            responseMessage.content = accumulatedContent
                            receivedCompleteResponse = True
                        continue

                    messageContent = ''
                    if jsonData.get('outputs') and isinstance(jsonData['outputs'], list):
                        for output in jsonData['outputs']:
                            if output.get('outputs') and isinstance(output['outputs'], list):
                                for inner_output in output['outputs']:
                                    if inner_output.get('results', {}).get('message', {}).get('text'):
                                        messageContent = inner_output['results']['message']['text']
                                        break
                    elif jsonData.get('choices') and jsonData['choices'][0].get('delta', {}).get('content'):
                        messageContent = jsonData['choices'][0]['delta']['content']
                    elif jsonData.get('text'):
                        messageContent = jsonData['text']
                    elif jsonData.get('response'):
                        messageContent = jsonData['response']

                    if messageContent:
                        accumulatedContent += messageContent
                        responseMessage.content = accumulatedContent
                        await asyncio.sleep(0)  # 让出控制权，确保UI更新

                except json.JSONDecodeError as e:
                    log.error(f'Error parsing JSON from stream: {e}, data: {data[:200]}')
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
