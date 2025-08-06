<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { getApiKeysConfig, updateApiKeysConfig } from '$lib/apis';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = false;
	let saving = false;

	// API密钥配置
	let apiKeysConfig = {
		langflow_api_key_masked: '',
		langflow_base_url: '',
		fastgpt_api_key_masked: '',
		fastgpt_base_url: '',
	};

	// 编辑状态的配置
	let editConfig = {
		langflow_api_key: '',
		langflow_base_url: '',
		fastgpt_api_key: '',
		fastgpt_base_url: '',
	};

	const loadApiKeysConfig = async () => {
		loading = true;
		try {
			const config = await getApiKeysConfig(localStorage.token);
			if (config) {
				apiKeysConfig = config;
				// 初始化编辑配置
				editConfig.langflow_base_url = config.langflow_base_url || '';
				editConfig.fastgpt_base_url = config.fastgpt_base_url || '';
			}
		} catch (error) {
			console.error('获取API密钥配置失败:', error);
			toast.error('获取API密钥配置失败');
		} finally {
			loading = false;
		}
	};

	const saveApiKeysConfig = async () => {
		saving = true;
		try {
			// 只提交有值的字段
			const updateData: any = {};

			if (editConfig.langflow_api_key?.trim()) {
				updateData.langflow_api_key = editConfig.langflow_api_key.trim();
			}
			if (editConfig.langflow_base_url?.trim()) {
				updateData.langflow_base_url = editConfig.langflow_base_url.trim();
			}
			if (editConfig.fastgpt_api_key?.trim()) {
				updateData.fastgpt_api_key = editConfig.fastgpt_api_key.trim();
			}
			if (editConfig.fastgpt_base_url?.trim()) {
				updateData.fastgpt_base_url = editConfig.fastgpt_base_url.trim();
			}

			if (Object.keys(updateData).length === 0) {
				toast.error('请至少填写一项配置');
				return;
			}

			const result = await updateApiKeysConfig(localStorage.token, updateData);
			if (result) {
				toast.success('API密钥配置保存成功');
				// 重新加载配置
				await loadApiKeysConfig();
				// 清空编辑框中的密钥
				editConfig.langflow_api_key = '';
				editConfig.fastgpt_api_key = '';
			}
		} catch (error) {
			console.error('保存API密钥配置失败:', error);
			toast.error(typeof error === 'string' ? error : '保存API密钥配置失败');
		} finally {
			saving = false;
		}
	};

	onMount(() => {
		loadApiKeysConfig();
	});
</script>

<div class="mb-3">
	<div class="mb-2.5 flex w-full items-center justify-between">
		<div class="text-base font-medium">API密钥配置</div>
	</div>

	<hr class="border-gray-100 dark:border-gray-850 my-2" />

	{#if loading}
		<div class="flex justify-center py-4">
			<Spinner />
		</div>
	{:else}
		<div class="space-y-2">
			<!-- WorldSeek Agent 配置 -->
			<div class="p-2">
				<div
					class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2"
				>
					WorldSeek Agent 配置
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div class="space-y-2">
						<label
							for="langflow-api-key"
							class="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							<span>API密钥</span>
							{#if apiKeysConfig.langflow_api_key_masked}
								<span
									class="text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded"
								>
									已配置: {apiKeysConfig.langflow_api_key_masked.slice(0, 4)}*******{apiKeysConfig.langflow_api_key_masked.slice(-4)}
								</span>
							{:else}
								<span
									class="text-xs text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-2 py-1 rounded"
								>
									未配置
								</span>
							{/if}
						</label>
						<input
							id="langflow-api-key"
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							placeholder="输入新的WorldSeek Agent API密钥"
							bind:value={editConfig.langflow_api_key}
						/>
					</div>

					<div class="space-y-2 flex flex-col">
						<label for="langflow-base-url" class="block text-sm font-medium text-gray-700 dark:text-gray-300 flex-1">
							API基础URL（注意：URL需保留 "/api/v1" 后缀）
						</label>
						<input
							id="langflow-base-url"
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="url"
							placeholder="例如: https://uat.worldseek-ai.com/api/v1，留空表示使用默认值"
							bind:value={editConfig.langflow_base_url}
						/>
					</div>
				</div>
			</div>

			<!-- FastGPT 配置 -->
			<div class="p-2">
				<div
					class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2"
				>
					FastGPT 配置
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div class="space-y-2">
						<label
							for="fastgpt-api-key"
							class="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300"
						>
							<span>API密钥</span>
							{#if apiKeysConfig.fastgpt_api_key_masked}
								<span
									class="text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded"
								>
									已配置: {apiKeysConfig.fastgpt_api_key_masked.slice(0, 4)}*******{apiKeysConfig.fastgpt_api_key_masked.slice(-4)}
								</span>
							{:else}
								<span
									class="text-xs text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-2 py-1 rounded"
								>
									未配置
								</span>
							{/if}
						</label>
						<input
							id="fastgpt-api-key"
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							placeholder="输入新的FastGPT API密钥"
							bind:value={editConfig.fastgpt_api_key}
						/>
					</div>

					<div class="space-y-2 flex flex-col">
						<label for="fastgpt-base-url" class="block text-sm font-medium text-gray-700 dark:text-gray-300 flex-1">
							API基础URL（注意：URL无需添加后缀，如：http://fastgpt.example.com:4000）
						</label>
						<input
							id="fastgpt-base-url"
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="url"
							placeholder="例如: http://fastgpt.example.com:4000，留空表示使用默认值"
							bind:value={editConfig.fastgpt_base_url}
						/>
					</div>
				</div>
			</div>

			<!-- 保存按钮 -->
			<div class="flex justify-end pt-2">
				<button
					class="header-btn btn-primary no-shadow"
					type="button"
					disabled={saving}
					on:click={saveApiKeysConfig}
				>
					{#if saving}
						<Spinner className="w-3 h-3" />
					{/if}
					{saving ? '保存中...' : '保存API配置'}
				</button>
			</div>

			<!-- 说明文字 -->
			<div
				class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
			>
				<div class="flex items-start gap-2">
					<div class="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5">
						<svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
							<path
								fill-rule="evenodd"
								d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class="flex-1">
						<p class="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">配置说明</p>
						<ul class="text-xs text-blue-700 dark:text-blue-300 space-y-1">
							<li>• 管理员配置的API密钥将被所有用户的工作流和知识库功能使用</li>
							<li>• API密钥以脱敏形式显示，只显示前4位和后4位字符</li>
							<li>• URL字段可选，未配置时将使用环境变量中的默认值</li>
							<li>• WorldSeek Agent用于工作流功能，FastGPT用于知识库功能</li>
						</ul>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
