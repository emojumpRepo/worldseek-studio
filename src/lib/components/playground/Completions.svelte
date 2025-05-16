<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings, showSidebar } from '$lib/stores';
	import { chatCompletion } from '$lib/apis/openai';
	import { runLangflowWorkflow } from '$lib/apis/chats';

	import { splitStream } from '$lib/utils';
	import Selector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import MenuLines from '../icons/MenuLines.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let text = '';

	let selectedModelId = '';

	let loading = false;
	let stopResponseFlag = false;

	let textCompletionAreaElement: HTMLTextAreaElement;

	const scrollToBottom = () => {
		const element = textCompletionAreaElement;

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const handleLangflowStream = async (res) => {
		let streamContent = '';

		try {
			if (res.body) {
				const reader = res.body.getReader();
				const decoder = new TextDecoder('utf-8');
				let receivedCompleteResponse = false; // 标记是否收到了完整响应

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
									toast.error(`Error: ${jsonData.error.detail || 'Error in Langflow stream'}`);
									continue;
								}
								
								// 处理完整响应消息
								if (jsonData.id === 'langflow-complete' && jsonData.complete === true) {
									console.log('收到完整响应内容，长度：', jsonData.content.length);
									// 如果后端提供了完整内容，则使用后端的完整内容
									if (jsonData.content && jsonData.content.length > 0) {
										streamContent = jsonData.content;
										text = streamContent;
										receivedCompleteResponse = true;
										await tick();
										scrollToBottom();
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
									streamContent += messageContent;
									text += messageContent;
									await tick();
									scrollToBottom();
								}
							} catch (e) {
								console.error('Error parsing JSON from stream:', e, data);
							}
						}
					}
				}
				
				// 流式完成后记录日志
				if (receivedCompleteResponse) {
					console.log('流式响应完成，使用后端提供的完整内容');
				} else {
					console.log('流式响应完成，使用前端累积的内容');
				}
			}
		} catch (error) {
			console.error('Error reading stream:', error);
			toast.error(`Stream error: ${error.message}`);
		}
		
		return streamContent;
	};

	const textCompletionHandler = async () => {
		const model = $models.find((model) => model.id === selectedModelId);
		if (!model) {
			toast.error('选择的模型不存在');
			return;
		}

		try {
			const useStream = true; // 默认使用流式响应
			const res = await runLangflowWorkflow(
				localStorage.token,
				model.base_app_id,
				[
					{
						role: 'assistant',
						content: text
					}
				],
				{
					stream: useStream
				}
			);

			if (res) {
				if (useStream && res.body) {
					// 处理流式响应
					await handleLangflowStream(res);
				} else if (res.error) {
					toast.error(`Error: ${res.error}`);
				} else {
					text += res.response || '';
					scrollToBottom();
				}
			}
		} catch (error) {
			console.error(error);
			toast.error(`${error}`);
		}
	};

	const submitHandler = async () => {
		if (selectedModelId) {
			loading = true;
			await textCompletionHandler();

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
	<div class="mx-auto w-full md:px-0 h-full">
		<div class=" flex flex-col h-full px-4">
			<div class="flex flex-col justify-between mb-1 gap-1">
				<div class="flex flex-col gap-1 w-full">
					<div class="flex w-full">
						<div class="overflow-hidden w-full">
							<div class="max-w-full">
								<Selector
									placeholder={$i18n.t('Select a model')}
									items={$models.map((model) => ({
										value: model.id,
										label: model.name,
										model: model
									}))}
									bind:value={selectedModelId}
								/>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div
				class=" pt-0.5 pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
				id="messages-container"
			>
				<div class=" h-full w-full flex flex-col">
					<div class="flex-1">
						<textarea
							id="text-completion-textarea"
							bind:this={textCompletionAreaElement}
							class="w-full h-full p-3 bg-transparent border border-gray-100 dark:border-gray-850 outline-hidden resize-none rounded-lg text-sm"
							bind:value={text}
							placeholder={$i18n.t("You're a helpful assistant.")}
						/>
					</div>
				</div>
			</div>

			<div class="pb-3 flex justify-end">
				{#if !loading}
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						on:click={() => {
							submitHandler();
						}}
					>
						{$i18n.t('Run')}
					</button>
				{:else}
					<button
						class="px-3 py-1.5 text-sm font-medium bg-gray-300 text-black transition rounded-full"
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

<style>
	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
