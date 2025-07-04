<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import {
		OLLAMA_API_BASE_URL,
		OPENAI_API_BASE_URL,
		WEBUI_API_BASE_URL,
		WEBUI_BASE_URL
	} from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings } from '$lib/stores';

	import { chatCompletion, generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { runLangflowWorkflow } from '$lib/apis/chats';

	import { splitStream } from '$lib/utils';
	import Collapsible from '../common/Collapsible.svelte';

	import Messages from '$lib/components/playground/Chat/Messages.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Pencil from '../icons/Pencil.svelte';
	import Cog6 from '../icons/Cog6.svelte';
	import Sidebar from '../common/Sidebar.svelte';
	import ArrowRight from '../icons/ArrowRight.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let selectedModelId = '';
	let loading = false;
	let stopResponseFlag = false;

	let systemTextareaElement: HTMLTextAreaElement;
	let messagesContainerElement: HTMLDivElement;

	let showSystem = false;
	let showSettings = false;

	let system = '';

	let role = 'user';
	let message = '';

	let messages = [];

	const scrollToBottom = () => {
		const element = messagesContainerElement;

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const resizeSystemTextarea = async () => {
		await tick();
		if (systemTextareaElement) {
			systemTextareaElement.style.height = '';
			systemTextareaElement.style.height = Math.min(systemTextareaElement.scrollHeight, 555) + 'px';
		}
	};

	$: if (showSystem) {
		resizeSystemTextarea();
	}

	const handleLangflowStream = async (res, responseMessage) => {
		if (!res || !res.body) {
			console.error('Invalid response from Langflow streaming API');
			return;
		}

		const reader = res.body.getReader();
		const decoder = new TextDecoder('utf-8');
		let accumulatedContent = responseMessage.content || ''; // 用于累积完整内容
		let receivedCompleteResponse = false; // 标记是否收到了完整响应

		try {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const chunk = decoder.decode(value, { stream: true });
				const lines = chunk.split('\n');

				for (const line of lines) {
					if (line.startsWith('data:')) {
						const data = line.slice(5).trim();
						if (data === '[DONE]') continue;

						try {
							const jsonData = JSON.parse(data);
							
							// 检查错误
							if (jsonData.error) {
								console.error('Langflow stream error:', jsonData.error);
								responseMessage.content = `Error: ${jsonData.error.detail || 'Error in Langflow stream'}`;
								continue;
							}
							
							// 处理完整响应消息
							if (jsonData.id === 'langflow-complete' && jsonData.complete === true) {
								console.log('收到完整响应内容，长度：', jsonData.content.length);
								// 如果后端提供了完整内容，则使用后端的完整内容
								if (jsonData.content && jsonData.content.length > 0) {
									accumulatedContent = jsonData.content;
									responseMessage.content = accumulatedContent;
									messages = messages;
									receivedCompleteResponse = true;
								}
								continue;
							}

							// 从不同格式中提取内容
							let messageContent = '';
							if (jsonData.choices && jsonData.choices[0]?.delta?.content) {
								// OpenAI格式
								messageContent = jsonData.choices[0].delta.content;
							} else if (jsonData.text) {
								// 纯文本格式
								messageContent = jsonData.text;
							} else if (jsonData.response) {
								// Langflow特定格式
								messageContent = jsonData.response;
							}

							if (messageContent) {
								accumulatedContent += messageContent; // 累积完整内容
								responseMessage.content = accumulatedContent; // 更新显示内容
								messages = messages;
								await tick();
								const textareaElement = document.getElementById(`assistant-${messages.length - 1}-textarea`);
								if (textareaElement) {
									textareaElement.style.height = textareaElement.scrollHeight + 'px';
								}
								scrollToBottom();
							}
						} catch (e) {
							console.error('Error parsing JSON from stream:', e, data);
						}
					}
				}
			}
		} catch (error) {
			console.error('Error reading stream:', error);
			responseMessage.content = `Stream error: ${error.message}`;
		} finally {
			// 确保最终内容被保存
			responseMessage.content = accumulatedContent;
			
			// 如果收到了完整响应，记录日志
			if (receivedCompleteResponse) {
				console.log('流式响应完成，使用后端提供的完整内容');
			} else {
				console.log('流式响应完成，使用前端累积的内容');
			}
			
			messages = messages;
			await tick();
			scrollToBottom();
		}
	};

	const chatCompletionHandler = async () => {
		if (selectedModelId === '') {
			toast.error($i18n.t('Please select a model.'));
			return;
		}

		const model = $models.find((model) => model.id === selectedModelId);
		if (!model) {
			selectedModelId = '';
			return;
		}

		const messageList = [
			...(system
				? [{
						role: 'system',
						content: system
					}]
				: []),
			...messages
		].filter((message) => message);

		let responseMessage;
		if (messages.at(-1)?.role === 'assistant') {
			responseMessage = messages.at(-1);
			responseMessage.content = '';
		} else {
			responseMessage = {
				role: 'assistant',
				content: ''
			};
			messages.push(responseMessage);
			messages = messages;
		}

		await tick();
		const textareaElement = document.getElementById(`assistant-${messages.length - 1}-textarea`);

		try {
			const useStream = true; // 默认使用流式响应
			const res = await runLangflowWorkflow(
				localStorage.token,
				model.base_app_id,
				model.id,
				messageList,
				{
					stream: useStream
				}
			);

			if (res) {
				if (useStream && res.body) {
					// 处理流式响应
					await handleLangflowStream(res, responseMessage);
				} else if (res.error) {
					// 处理错误响应
					toast.error(`Error: ${res.error}`);
					responseMessage.content = `Error: ${res.error}`;
				} else {
					// 处理非流式响应
					responseMessage.content = res.response || '';
					textareaElement.style.height = textareaElement.scrollHeight + 'px';
					messages = messages;
					scrollToBottom();
				}
			}
		} catch (error) {
			console.error(error);
			toast.error(`${error}`);
			responseMessage.content = `Error: ${error}`;
			messages = messages;
		}
	};

	const addHandler = async () => {
		if (message) {
			messages.push({
				role: role,
				content: message
			});
			messages = messages;
			message = '';
			await tick();
			scrollToBottom();
		}
	};

	const submitHandler = async () => {
		if (selectedModelId) {
			await addHandler();

			loading = true;
			await chatCompletionHandler();

			loading = false;
			stopResponseFlag = false;
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}

		if ($settings?.models) {
			selectedModelId = $settings?.models[0];
		} else if ($config?.default_models) {
			selectedModelId = $config?.default_models.split(',')[0];
		} else {
			selectedModelId = '';
		}
		loaded = true;
	});
</script>

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full relative">
		<Sidebar bind:show={showSettings} className=" bg-white dark:bg-gray-900" width="300px">
			<div class="flex flex-col px-5 py-3 text-sm">
				<div class="flex justify-between items-center mb-2">
					<div class=" font-medium text-base">Settings</div>

					<div class=" translate-x-1.5">
						<button
							class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
							on:click={() => {
								showSettings = !showSettings;
							}}
						>
							<ArrowRight className="size-3" strokeWidth="2.5" />
						</button>
					</div>
				</div>

				<div class="mt-1">
					<div>
						<div class=" text-xs font-medium mb-1">Model</div>

						<div class="w-full">
							<select
								class="w-full bg-transparent border border-gray-100 dark:border-gray-850 rounded-lg py-1 px-2 -mx-0.5 text-sm outline-hidden"
								bind:value={selectedModelId}
							>
								{#each $models as model}
									<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name}</option>
								{/each}
							</select>
						</div>
					</div>
				</div>
			</div>
		</Sidebar>

		<div class=" flex flex-col h-full px-3.5">
			<div class="flex w-full items-start gap-1.5">
				<Collapsible
					className="w-full flex-1"
					bind:open={showSystem}
					buttonClassName="w-full rounded-lg text-sm border border-gray-100 dark:border-gray-850 w-full py-1 px-1.5"
					grow={true}
				>
					<div class="flex gap-2 justify-between items-center">
						<div class=" shrink-0 font-medium ml-1.5">
							{$i18n.t('System Instructions')}
						</div>

						{#if !showSystem}
							<div class=" flex-1 text-gray-500 line-clamp-1">
								{system}
							</div>
						{/if}

						<div class="shrink-0">
							<button class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg">
								{#if showSystem}
									<ChevronUp className="size-3.5" />
								{:else}
									<Pencil className="size-3.5" />
								{/if}
							</button>
						</div>
					</div>

					<div slot="content">
						<div class="pt-1 px-1.5">
							<textarea
								bind:this={systemTextareaElement}
								class="w-full h-full bg-transparent resize-none outline-hidden text-sm"
								bind:value={system}
								placeholder={$i18n.t("You're a helpful assistant.")}
								on:input={() => {
									resizeSystemTextarea();
								}}
								rows="4"
							/>
						</div>
					</div>
				</Collapsible>

				<div class="translate-y-1">
					<button
						class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
						on:click={() => {
							showSettings = !showSettings;
						}}
					>
						<Cog6 />
					</button>
				</div>
			</div>

			<div
				class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
				id="messages-container"
				bind:this={messagesContainerElement}
			>
				<div class=" h-full w-full flex flex-col">
					<div class="flex-1 p-1">
						<Messages bind:messages />
					</div>
				</div>
			</div>

			<div class="pb-3">
				<div class="text-xs font-medium text-gray-500 px-2 py-1">
					{selectedModelId}
				</div>
				<div class="border border-gray-100 dark:border-gray-850 w-full px-3 py-2.5 rounded-xl">
					<div class="py-0.5">
						<!-- $i18n.t('a user') -->
						<!-- $i18n.t('an assistant') -->
						<textarea
							bind:value={message}
							class=" w-full h-full bg-transparent resize-none outline-hidden text-sm"
							placeholder={$i18n.t(`Enter {{role}} message here`, {
								role: role === 'user' ? $i18n.t('a user') : $i18n.t('an assistant')
							})}
							on:input={(e) => {
								e.target.style.height = '';
								e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
							}}
							on:focus={(e) => {
								e.target.style.height = '';
								e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
							}}
							rows="2"
						/>
					</div>

					<div class="flex justify-between">
						<div>
							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-gray-50 hover:bg-gray-100 text-gray-900 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition rounded-lg"
								on:click={() => {
									role = role === 'user' ? 'assistant' : 'user';
								}}
							>
								{#if role === 'user'}
									{$i18n.t('User')}
								{:else}
									{$i18n.t('Assistant')}
								{/if}
							</button>
						</div>

						<div>
							{#if !loading}
								<button
									disabled={message === ''}
									class="px-3.5 py-1.5 text-sm font-medium disabled:bg-gray-50 dark:disabled:hover:bg-gray-850 disabled:cursor-not-allowed bg-gray-50 hover:bg-gray-100 text-gray-900 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition rounded-lg"
									on:click={() => {
										addHandler();
										role = role === 'user' ? 'assistant' : 'user';
									}}
								>
									{$i18n.t('Add')}
								</button>

								<button
									class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg"
									on:click={() => {
										submitHandler();
									}}
								>
									{$i18n.t('Run')}
								</button>
							{:else}
								<button
									class="px-3 py-1.5 text-sm font-medium bg-gray-300 text-black transition rounded-lg"
									on:click={() => {
										stopResponse();
									}}
								>
									{$i18n.t('Cancel')}
								</button>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
