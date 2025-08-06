<script lang="ts">
	import ModelSettingDialog from './Models/ModelSettingDialog.svelte';
	import ModelCreateDialog from './Models/ModelCreateDialog.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { toast } from 'svelte-sonner';
	import type { Agent } from '$lib/types';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, mobile, models as _models, settings, user } from '$lib/stores';
	import {
		deleteModelById,
		getModels as getWorkspaceModels,
		updateModelById,
		createNewModel,
		getWorkflowApps
	} from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import { getGroups } from '$lib/apis/groups';
	import Spinner from '../common/Spinner.svelte';
	import { eventBus } from '$lib/stores';

	import { WS_FLOW_BASE_URL } from '$lib/constants';

	let shiftKey = false;
	let loaded = false;

	let selectedAgent: Agent = {
		id: '',
		name: '',
		description: '',
		access_control: {},
		base_app_id: '',
		user_id: ''
	};

	let models: Agent[] = [];

	let filteredModels: Agent[] = [];

	let showModelSettingDialog = false;
	let showModelCreateDialog = false;
	let group_ids: string[] = [];

	$: if (models) {
		// 先根据搜索条件过滤
		const searchFiltered = models.filter(
			(m) => searchValue === '' || m.name.toLowerCase().includes(searchValue.toLowerCase())
		);

		// 分离有效和失效的智能体
		const validAgents = searchFiltered.filter((m) => m.workflow_app !== null);
		const invalidAgents = searchFiltered.filter((m) => m.workflow_app === null);

		// 分别按更新时间降序排序
		const sortByUpdateTime = (a: any, b: any) => {
			const aTime = new Date(a.updated_at || a.created_at || 0).getTime();
			const bTime = new Date(b.updated_at || b.created_at || 0).getTime();
			return bTime - aTime; // 降序排序
		};

		validAgents.sort(sortByUpdateTime);
		invalidAgents.sort(sortByUpdateTime);

		// 合并结果：有效的在前，失效的在后
		filteredModels = [...validAgents, ...invalidAgents];
	}

	let searchValue = '';

	const deleteModelHandler = async (e: CustomEvent<Agent>) => {
		console.log('deleteModelHandler e', e);
		const res = await deleteModelById(localStorage.token, e.detail.id).catch((e) => {
			toast.error($i18n.t(`Model {{name}} Settings Delete Failed`, { name: e.detail.name }));
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Model {{name}} Settings Delete Success`, { name: e.detail.name }));
			showModelSettingDialog = false;
		} else {
			toast.error($i18n.t(`Model {{name}} Settings Delete Failed`, { name: e.detail.name }));
		}

		await _models.set(await getModels(localStorage.token));
		models = await getWorkspaceModels(localStorage.token);
	};

	const saveModelHandler = async (e: CustomEvent<Agent>) => {
		console.log('saveModelHandler', e.detail);
		const res = await updateModelById(localStorage.token, e.detail.id, e.detail).catch((e) => {
			toast.error($i18n.t(`Model APP Settings Save Failed`));
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Model APP Settings Save Success`));
			showModelSettingDialog = false;
		} else {
			toast.error($i18n.t(`Model APP Settings Save Failed`));
		}

		await _models.set(await getModels(localStorage.token));
		models = await getWorkspaceModels(localStorage.token);
	};

	const createModelHandler = async (e: CustomEvent<Agent>) => {
		console.log('createModelHandler', e.detail);
		const res = await createNewModel(localStorage.token, e.detail).catch((e) => {
			toast.error($i18n.t(`Model Create Failed`));
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Model Create Success`));
			showModelCreateDialog = false;
		} else {
			toast.error($i18n.t(`Model Create Failed`));
		}

		await _models.set(await getModels(localStorage.token));
		models = await getWorkspaceModels(localStorage.token);
	};

	onMount(async () => {
		models = await getWorkspaceModels(localStorage.token);
		const workflowApps = await getWorkflowApps(localStorage.token, true);
		console.log('workflowApps', workflowApps);
		console.log('models', models);
		let groups = await getGroups(localStorage.token);
		group_ids = groups.map((group: any) => group.id);

		loaded = true;

		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event: KeyboardEvent) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur-sm', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur-sm', onBlur);
		};
	});

	// 订阅eventBus的变化
	$: if ($eventBus.showCreateDialog) {
		console.log('showCreateDialog', $eventBus.showCreateDialog);
		// 显示创建弹窗
		showModelCreateDialog = true;
		// 重置状态
		eventBus.update((bus) => ({ ...bus, showCreateDialog: false }));
	}

	// 智能体开发 - 跳转到外部开发网站
	const navigateToDevelop = () => {
		window.open(WS_FLOW_BASE_URL, '_blank');
	};

	const openCreateDialog = () => {
		console.log('打开新建智能体弹窗');
		showModelCreateDialog = true;
	};

	const updateWorkflowApps = async () => {
		models = await getWorkspaceModels(localStorage.token);
	};

	let deleteConfirmDialogShow = false;
	// 删除失效智能体的处理函数
	const deleteInvalidAgent = async (agent: Agent) => {
		try {
			const res = await deleteModelById(localStorage.token, agent.id);
			if (res) {
				toast.success(`智能体"${agent.name}"删除成功`);
				// 重新加载智能体列表
				models = await getWorkspaceModels(localStorage.token);
				await _models.set(await getModels(localStorage.token));
			} else {
				toast.error(`删除智能体"${agent.name}"失败`);
			}
		} catch (error) {
			console.error('删除智能体失败:', error);
			toast.error(`删除智能体"${agent.name}"失败`);
		}
	};
</script>

<svelte:head>
	<title>
		{$i18n.t('Models')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<ModelSettingDialog
		bind:show={showModelSettingDialog}
		bind:agent={selectedAgent}
		on:confirm={saveModelHandler}
		on:delete={deleteModelHandler}
	/>

	<DeleteConfirmDialog
		bind:show={deleteConfirmDialogShow}
		title="删除智能体"
		message="确定删除该智能体吗？"
		on:cancel={() => {
			deleteConfirmDialogShow = false;
		}}
		on:confirm={() => {
			deleteInvalidAgent(selectedAgent);
		}}
	/>

	<ModelCreateDialog
		bind:show={showModelCreateDialog}
		on:confirm={createModelHandler}
		on:updateWorkflowApps={updateWorkflowApps}
	/>

	<div class="my-4 mb-5">
		<div class="flex justify-between items-center mb-6">
			<div class="flex items-center gap-4">
				<h2 class="text-2xl font-bold text-gray-900 dark:text-white">智能体列表</h2>
				<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
					<span class="px-2 py-1 bg-black text-white rounded-full font-medium">
						{filteredModels.length} 个智能体
					</span>
				</div>
			</div>
			<div class="flex items-center gap-3">
				<!-- 搜索框 -->
				<div class="relative">
					<svg
						class="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400"
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
						/>
					</svg>
					<input
						type="text"
						placeholder="搜索智能体..."
						bind:value={searchValue}
						class="pl-10 pr-4 py-2 w-64 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
					/>
				</div>

				<!-- 智能体开发按钮 -->
				<button class="header-btn btn-secondary" on:click={navigateToDevelop}>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-4 w-4"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
						/>
					</svg>
					<span class="hidden sm:inline">智能体开发</span>
					<!-- 外部链接图标 -->
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-3 w-3 ml-1 opacity-60"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
						/>
					</svg>
				</button>

				<!-- 新建智能体按钮 -->
				<button class="header-btn btn-primary" on:click={openCreateDialog}>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-4 w-4"
						viewBox="0 0 20 20"
						fill="currentColor"
					>
						<path
							fill-rule="evenodd"
							d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
							clip-rule="evenodd"
						/>
					</svg>
					<span>新建智能体</span>
				</button>
			</div>
		</div>

		{#if filteredModels.length === 0}
			<div class="w-full flex flex-col justify-center items-center gap-4 py-8 mt-15">
				<div class="text-gray-400">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-12 w-12"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="1.5"
							d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
						/>
					</svg>
				</div>
				<p class="text-gray-500 text-lg font-medium">暂无智能体</p>
				<p class="text-gray-400 text-sm">点击右上角的"+"按钮创建新的智能体</p>
			</div>
		{:else}
			<div class="gap-4 grid lg:grid-cols-2 xl:grid-cols-3" id="model-list">
				{#each filteredModels as model}
					<div class="agent-card {model.workflow_app === null ? 'disabled' : ''}">
						<!-- 失效标签 -->
						{#if model.workflow_app === null}
							<div class="expired-tag">已失效</div>
						{/if}

						<div class="agent-header">
							<div class="agent-avatar">
								<span class="agent-initial">{model.name.charAt(0)}</span>
							</div>
							<div class="agent-info">
								<h3 class="agent-name">{model.name}</h3>
								<div class="agent-mode {model.access_control ? 'mode-private' : 'mode-public'}">
									{#if model.access_control}
										<svg
											xmlns="http://www.w3.org/2000/svg"
											class="mode-icon"
											viewBox="0 0 20 20"
											fill="currentColor"
										>
											<path
												fill-rule="evenodd"
												d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
												clip-rule="evenodd"
											/>
										</svg>
										<span>私有模式</span>
									{:else}
										<svg
											xmlns="http://www.w3.org/2000/svg"
											class="mode-icon"
											viewBox="0 0 20 20"
											fill="currentColor"
										>
											<path
												fill-rule="evenodd"
												d="M10 18a8 8 0 100-16 8 8 0 000 16zM4.332 8.027a6.012 6.012 0 011.912-2.706C6.512 5.73 6.974 6 7.5 6A1.5 1.5 0 019 7.5V8a2 2 0 004 0 2 2 0 011.523-1.943A5.977 5.977 0 0110 2c-1.61 0-3.09.62-4.19 1.64a.75.75 0 010 1.06A5.99 5.99 0 0111 5.3c.3 0 .58.02.86.05.03.3.05.6.05.9V8a3 3 0 01-6 0V7.5a.5.5 0 00-1 0V8a4 4 0 108 0c0-.17-.01-.33-.03-.49a6 6 0 01-9.65 6.11.75.75 0 010-1.06A5.99 5.99 0 0110 14c.34 0 .67-.03 1-.1V10a.75.75 0 000-1.5v3.73c.84-.31 1.63-.84 2.27-1.57a.75.75 0 10-1.38-.91 4.62 4.62 0 01-3.89 2.2c-1.25 0-2.41-.5-3.3-1.29a.75.75 0 00-1.06 0A5.972 5.972 0 0110 18c3.31 0 6-2.69 6-6 0-.32-.03-.63-.08-.93a.748.748 0 00-.26-1.08c-.13-.09-.27-.16-.42-.21h-.01V8a3 3 0 00-3-3 3 3 0 00-3 3 .5.5 0 01-1 0z"
												clip-rule="evenodd"
											/>
										</svg>
										<span>公开模式</span>
									{/if}
								</div>
							</div>
						</div>

						<div class="agent-description">
							{model.description || '无描述'}
						</div>

						<div class="agent-footer">
							<div class="flex gap-2">
								<button
									class="agent-action-btn"
									disabled={model.workflow_app === null}
									on:click={() => {
										if (model.workflow_app !== null) {
											showModelSettingDialog = true;
											selectedAgent = model;
										}
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										class="h-5 w-5"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
										/>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
										/>
									</svg>
									设置
								</button>

								{#if model.workflow_app === null}
									<button
										class="agent-remove-btn"
										on:click={() => {
											deleteConfirmDialogShow = true;
											selectedAgent = model;
										}}
										title="删除失效的智能体"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											class="h-5 w-5"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1-1H9a1 1 0 00-1 1v3M4 7h16"
											/>
										</svg>
										移除
									</button>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}

<style>
	.btn-secondary {
		background-color: white;
		color: #6b7280;
		border-color: #e5e7eb;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}

	.btn-secondary:hover {
		background-color: #f9fafb;
		color: #374151;
		border-color: #d1d5db;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	/* 暗色模式支持 */
	:global(.dark) .btn-secondary {
		background-color: #374151;
		color: #d1d5db;
		border-color: #4b5563;
	}

	:global(.dark) .btn-secondary:hover {
		background-color: #4b5563;
		color: #f3f4f6;
		border-color: #6b7280;
	}

	/* 响应式设计 */
	@media (max-width: 640px) {
		.header-btn {
			padding: 8px 12px;
			font-size: 0.8rem;
		}

		.header-btn span {
			display: none;
		}
	}

	.agent-card {
		background-color: white;
		border-radius: 12px;
		padding: 20px;
		border: 1px solid #e5e7eb;
		transition: all 0.15s ease;
		display: flex;
		flex-direction: column;
		height: 100%;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
		position: relative;
	}

	.agent-card:hover {
		border-color: #3b82f6;
		box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
	}

	/* 禁用状态样式 - 不使用整体透明度，而是用伪元素遮罩 */
	.agent-card.disabled {
		background-color: #f8f9fa;
		border-color: #dee2e6;
		user-select: none;
	}

	/* 失效卡片内容区域禁用点击，但按钮区域可以点击 */
	.agent-card.disabled .agent-header,
	.agent-card.disabled .agent-description {
		pointer-events: none;
	}

	/* 移除按钮在失效卡片中仍然可以点击且在遮罩层之上 */
	.agent-card.disabled .agent-remove-btn {
		pointer-events: auto !important;
		position: relative;
		z-index: 20; /* 确保在遮罩层(z-index: 2)之上 */
	}

	.agent-card.disabled:hover {
		border-color: #dee2e6;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
	}

	/* 失效标签样式 */
	.expired-tag {
		position: absolute;
		top: 12px;
		right: 12px;
		background-color: #fef2f2;
		color: #dc2626;
		border: 1px solid #fecaca;
		border-radius: 6px;
		padding: 4px 8px;
		font-size: 0.75rem;
		font-weight: 500;
		display: flex;
		align-items: center;
		gap: 4px;
		z-index: 1;
	}

	.agent-header {
		display: flex;
		align-items: center;
		gap: 14px;
		margin-bottom: 14px;
	}

	.agent-avatar {
		width: 42px;
		height: 42px;
		border-radius: 10px;
		background-color: #e0e7ff;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.agent-initial {
		font-weight: 600;
		font-size: 18px;
		color: #4f46e5;
	}

	.agent-info {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.agent-name {
		font-weight: 600;
		font-size: 1rem;
		color: #111827;
		margin: 0;
	}

	.agent-mode {
		font-size: 0.75rem;
		padding: 2px 8px;
		border-radius: 20px;
		display: flex;
		align-items: center;
		gap: 4px;
		width: fit-content;
	}

	.mode-icon {
		width: 14px;
		height: 14px;
	}

	.mode-public {
		color: #047857;
		background-color: #ecfdf5;
		border: 1px solid #a7f3d0;
	}

	.mode-private {
		color: #7c3aed;
		background-color: #f5f3ff;
		border: 1px solid #ddd6fe;
	}

	:global(.dark) .mode-public {
		color: #10b981;
		background-color: rgba(16, 185, 129, 0.1);
		border: 1px solid rgba(16, 185, 129, 0.2);
	}

	:global(.dark) .mode-private {
		color: #a78bfa;
		background-color: rgba(167, 139, 250, 0.1);
		border: 1px solid rgba(167, 139, 250, 0.2);
	}

	.agent-description {
		font-size: 0.9rem;
		color: #4b5563;
		flex-grow: 1;
		line-height: 1.5;
		margin-bottom: 16px;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		min-height: 2.7rem; /* 固定高度为两行：1.5行高 × 2行 × 0.9rem字体大小 */
		height: 2.7rem;
	}

	.agent-footer {
		display: flex;
		justify-content: flex-end;
		margin-top: auto;
		padding-top: 12px;
		border-top: 1px solid #f3f4f6;
		position: relative;
		z-index: 10; /* 确保footer区域在遮罩层之上 */
	}

	.agent-action-btn {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 8px 12px;
		font-size: 0.875rem;
		font-weight: 500;
		color: #4b5563;
		border-radius: 8px;
		border: 1px solid #e5e7eb;
		background-color: #f9fafb;
		transition: all 0.15s ease;
	}

	.agent-action-btn:hover {
		background-color: #f3f4f6;
		border-color: #d1d5db;
		color: #1f2937;
	}

	.agent-action-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
		background-color: #f9fafb;
		border-color: #e5e7eb;
		color: #9ca3af;
	}

	.agent-action-btn:disabled:hover {
		background-color: #f9fafb;
		border-color: #e5e7eb;
		color: #9ca3af;
	}

	.agent-remove-btn {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 8px 12px;
		font-size: 0.875rem;
		font-weight: 600;
		color: #ff4848;
		border-radius: 8px;
		background-color: #fff;
		border: 1px solid #ff4848;
		transition: all 0.15s ease;
		cursor: pointer;
		pointer-events: auto !important; /* 确保按钮始终可点击 */
		position: relative;
		z-index: 10; /* 提升层级，确保在失效遮罩之上 */
		box-shadow: 0 2px 4px rgba(220, 38, 38, 0.2);
		opacity: 1 !important; /* 强制不透明，不受父元素影响 */
	}

	.agent-remove-btn:hover {
		background-color: #b91c1c;
		border-color: #b91c1c;
		color: #ffffff;
		box-shadow: 0 4px 8px rgba(220, 38, 38, 0.3);
		transform: translateY(-1px);
	}

	@media (prefers-color-scheme: dark) {
		.agent-card {
			background-color: #1f2937;
			border-color: #374151;
		}

		.agent-card:hover {
			border-color: #3b82f6;
			box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
		}

		.agent-card.disabled {
			background-color: #1a1f2a;
			border-color: #2d3748;
		}

		/* 暗色模式下的失效遮罩 */
		:global(.dark) .agent-card.disabled::before {
			background-color: rgba(0, 0, 0, 0.6);
		}

		/* 暗色模式下失效卡片的点击控制 */
		:global(.dark) .agent-card.disabled .agent-header,
		:global(.dark) .agent-card.disabled .agent-description {
			pointer-events: none;
		}

		:global(.dark) .agent-card.disabled .agent-remove-btn {
			pointer-events: auto !important;
			position: relative;
			z-index: 20; /* 确保在遮罩层之上 */
		}

		.expired-tag {
			background-color: #3f2937;
			color: #fca5a5;
			border-color: #702459;
		}

		.agent-avatar {
			background-color: #2e3a4f;
		}

		.agent-initial {
			color: #93c5fd;
		}

		.agent-name {
			color: #f3f4f6;
		}

		.agent-mode {
			background-color: #374151;
			color: #d1d5db;
		}

		.agent-description {
			color: #d1d5db;
		}

		.agent-footer {
			border-top-color: #374151;
		}

		.agent-action-btn {
			background-color: #374151;
			border-color: #4b5563;
			color: #e5e7eb;
		}

		.agent-action-btn:hover {
			background-color: #4b5563;
			border-color: #6b7280;
			color: #f9fafb;
		}

		.agent-action-btn:disabled {
			background-color: #374151;
			border-color: #4b5563;
			color: #6b7280;
		}

		.agent-action-btn:disabled:hover {
			background-color: #374151;
			border-color: #4b5563;
			color: #6b7280;
		}

		.agent-remove-btn {
			background-color: #dc2626;
			border-color: #dc2626;
			color: #ffffff;
			position: relative;
			z-index: 10;
			opacity: 1 !important;
			box-shadow: 0 2px 4px rgba(220, 38, 38, 0.3);
		}

		.agent-remove-btn:hover {
			background-color: #b91c1c;
			border-color: #b91c1c;
			color: #ffffff;
			box-shadow: 0 4px 8px rgba(220, 38, 38, 0.4);
			transform: translateY(-1px);
		}
	}
</style>
