<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { fade } from 'svelte/transition';
	import { Label, RadioGroup } from 'bits-ui';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import CirclePlus from '$lib/components/icons/CirclePlus.svelte';
	import Close from '$lib/components/icons/Close.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import DropdownSelect from '$lib/components/common/DropdownSelect.svelte';
    import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import type { Agent } from '$lib/types';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let agent: Agent = {
		id: '',
		name: '',
		description: '',
		base_app_id: '',
		user_id: '',
		params: {
			model: '',
			prompt: '',
			knowledge: {
				settings: {
					searchMode: 'vector',
					useLimit: 10,
					relevance: 0.5,
					contentReordering: false,
					optimization: false
				},
				items: []
			},
			tools: []
		},
		access_control: {}
	};

	// 确保agent的params属性始终存在且完整
	$: {
		const defaultParams = {
			model: '',
			prompt: '',
			knowledge: {
				settings: {
					searchMode: 'vector',
					useLimit: 10,
					relevance: 0.5,
					contentReordering: false,
					optimization: false
				},
				items: []
			},
			tools: []
		};

		if (!agent.params) {
			agent.params = {
				...defaultParams,
				...(agent.workflow_app?.params || {})
			};
		} else {
			agent.params = {
				...defaultParams,
				...(agent.workflow_app?.params || {}),
				...agent.params
			};
		}
	}
	
	// 初始化描述信息（首次显示时）
	let isFirstShow = true;
    $: if (show && isFirstShow) {
        isFirstShow = false;
        if (!agent.description) {
            agent.description = agent.workflow_app?.description || '';
        }
    }

	// 从agent.access_control派生accessControl值
	let accessControl = 'private';
	$: accessControl = agent.access_control ? 'private' : 'public';

	// 当RadioGroup选择变化时手动更新agent
	function handleAccessChange(value: string) {
		if (value === 'public') {
			agent.access_control = null;
		} else {
			agent.access_control = {};
		}
	}

	const modelList = [
		{
			label: 'GPT-3.5-turbo',
			value: 'gpt-3.5-turbo'
		},
		{
			label: 'GPT-4',
			value: 'gpt-4'
		},
		{
			label: 'GPT-4-turbo',
			value: 'gpt-4-turbo'
		},
		{
			label: 'GPT-4-turbo-preview',
			value: 'gpt-4-turbo-preview'
		},
		{
			label: 'GPT-4-turbo-preview-2',
			value: 'gpt-4-turbo-preview-2'
		}
	];

	const searchModeList = [
		{
			label: '向量',
			value: 'vector'
		}
	];

	let modalElement: HTMLElement | null = null;
	let mounted = false;
	let isClosing = false;
	let deleteConfirmDialogShow = false;

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			closeModal();
		}
	};

	// 关闭弹窗
	const closeModal = () => {
		if (isClosing) return;
		isClosing = true;
		setTimeout(() => {
			isClosing = false;
			show = false;
			isFirstShow = true; // 重置标志，以便下次打开弹窗时再次设置默认描述
		}, 200); // 动画持续时间
	};

    // 保存智能体设置
	const confirmHandler = async () => {
        // 如果描述信息为空，则设置为官方应用的描述信息
        if(!agent.description) {
            agent.description = agent.workflow_app?.description || '';
        }
        dispatch('confirm', agent);
	};

	// 删除知识库
	function removeKnowledgeItem(index: number) {
		if (agent.params) {
			agent.params.knowledge.items = agent.params.knowledge.items.filter((_, i) => i !== index);
		}
	}

    // 删除工具
    function removeTool(index: number) {
        if (agent.params) {
            agent.params.tools = agent.params.tools.filter((_, i) => i !== index);
        }
    }

	onMount(() => {
		mounted = true;
	});

	$: if (mounted) {
		if (show && modalElement) {
			document.body.appendChild(modalElement);

			window.addEventListener('keydown', handleKeyDown);
			document.body.style.overflow = 'hidden';
		} else if (modalElement) {
			window.removeEventListener('keydown', handleKeyDown);
			document.body.removeChild(modalElement);

			document.body.style.overflow = 'unset';
		}
	}
</script>
<DeleteConfirmDialog
	bind:show={deleteConfirmDialogShow}
	title='删除智能体'
	message='确定删除该智能体吗？'
	on:cancel={() => {
		deleteConfirmDialogShow = false;
	}}
	on:confirm={() => {
		dispatch('delete', agent);
	}}
/>
{#if show || isClosing}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={modalElement}
		class="modal-backdrop"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			closeModal();
		}}
	>
		<div
			class="modal-content m-auto rounded-lg max-w-full w-[35rem] mx-2 bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950 max-h-[90vh] shadow-3xl flex flex-col {isClosing
				? 'modal-closing'
				: ''}"
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<!-- 设置弹窗头部（标题和关闭按钮） -->
			<div class="modal-header px-5 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-900/70 dark:to-gray-800/70 rounded-t-lg">
				<div class="font-semibold text-base text-gray-800 dark:text-gray-200">
					{$i18n.t('Model APP Settings')}
				</div>
				<button
					class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors p-1.5 rounded-full hover:bg-gray-200/50 dark:hover:bg-gray-800/50"
					on:pointerdown={(e) => {
						e.stopImmediatePropagation();
						e.preventDefault();
						closeModal();
					}}
					on:click={(e) => {
						closeModal();
					}}
				>
					<Close className="w-5 h-5" />
				</button>
			</div>

			<!-- 表单部分 - 添加滚动 -->
			<div class="p-5 flex-1 overflow-y-auto">
				<div class="flex flex-col gap-6 text-sm">
					<!-- 智能体名称 表单项 -->
					<div class="form-group">
						<div class="form-header mb-2">
							<div class="form-title text-gray-800 dark:text-gray-200">
								{$i18n.t('Model Name')}
							</div>
							<div class="text-gray-500 dark:text-gray-400 text-xs">{agent.workflow_app?.name || ''}</div>
						</div>
						<input
							type="text"
							class="form-input"
							bind:value={agent.name}
							placeholder={$i18n.t('Model Name Placeholder')}
						/>
					</div>

					<!-- 智能体介绍 表单项 -->
					<div class="form-group">
						<div class="form-title mb-2 text-gray-800 dark:text-gray-200">
							{$i18n.t('Model Description')}
						</div>
						<textarea
							class="form-input"
							bind:value={agent.description}
							placeholder={$i18n.t('Model Description Placeholder')}
							rows={3}
						/>
					</div>

					<!-- 智能体访问权限 表单项 -->
					<div class="form-group p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-100 dark:border-gray-800 shadow-sm">
						<div class="form-title mb-3 text-gray-800 dark:text-gray-200">
							{$i18n.t('Models Access')}
						</div>
						<RadioGroup.Root
							class="flex gap-6 font-medium"
							value={accessControl}
							onValueChange={handleAccessChange}
						>
							<div class="text-gray-700 dark:text-gray-300 group flex select-none items-center transition-all">
								<RadioGroup.Item
									id="private"
									value="private"
									class="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-indigo-400 dark:hover:border-indigo-500 data-[state=checked]:border-4 data-[state=checked]:border-indigo-500 size-5 shrink-0 cursor-pointer rounded-full border transition-all duration-100 ease-in-out"
								/>
								<Label.Root for="private" class="pl-3 text-sm cursor-pointer"
									>{$i18n.t('Models Access Private')}</Label.Root
								>
							</div>
							<div class="text-gray-700 dark:text-gray-300 group flex select-none items-center transition-all">
								<RadioGroup.Item
									id="public"
									value="public"
									class="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-indigo-400 dark:hover:border-indigo-500 data-[state=checked]:border-4 data-[state=checked]:border-indigo-500 size-5 shrink-0 cursor-pointer rounded-full border transition-all duration-100 ease-in-out"
								/>
								<Label.Root for="public" class="pl-3 text-sm cursor-pointer">{$i18n.t('Models Access Public')}</Label.Root>
							</div>
						</RadioGroup.Root>
					</div>

					<!-- 智能体入参 表单项 -->
					<div class="flex flex-col gap-4">
						<div class="form-title text-gray-800 dark:text-gray-200 border-b border-gray-200 dark:border-gray-800 pb-2">
							{$i18n.t('Models Params')}
						</div>
						<!-- 模型选择 -->
						<div class="form-panel">
							<div class="form-panel-header mb-3">
								<div class="form-title text-gray-800 dark:text-gray-200">
									{$i18n.t('Models Model Choice')}
								</div>
								<button class="icon-button">
									<Cog6 />
									<span class="text-xs">{$i18n.t('Settings')}</span>
								</button>
							</div>
							<hr class="form-divider mb-3" />

							<DropdownSelect
								bind:value={agent.params.model}
								options={modelList}
								placeholder="请选择模型"
							/>
						</div>
						<!-- 提示词 -->
						<div class="form-panel">
							<div class="form-panel-header mb-3">
								<div class="form-title text-gray-800 dark:text-gray-200">
									{$i18n.t('Models Prompt')}
								</div>
							</div>
							<hr class="form-divider mb-3" />
							<textarea
								class="form-textarea"
								bind:value={agent.params.prompt}
								placeholder={$i18n.t('Models Prompt Placeholder')}
								rows={4}
							/>
						</div>
						<!-- 知识库选择 -->
						<div class="form-panel gradient-panel">
							<div class="form-panel-header mb-4">
								<div class="form-title text-gray-800 dark:text-gray-200">
									{$i18n.t('Models Knowledge Base')}
								</div>
								<div class="flex items-center gap-3">
									<button class="icon-button">
										<Cog6 />
										<span class="text-xs">{$i18n.t('Settings')}</span>
									</button>
									<button class="icon-button accent-button">
										<CirclePlus />
										<span class="text-xs">{$i18n.t('Add')}</span>
									</button>
								</div>
							</div>
							<div class="grid grid-cols-5 gap-6 text-xs mb-5 p-4 bg-white dark:bg-gray-900 rounded-lg border border-gray-100 dark:border-gray-800">
								<!-- 搜索模式 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title text-gray-700 dark:text-gray-300 mb-1 text-center">
										{$i18n.t('Models KnowledgeBase Search Mode')}
									</div>
									<DropdownSelect
										bind:value={agent.params.knowledge.settings.searchMode}
										options={searchModeList}
										isShowIcon={false}
										labelClass="text-xs"
										height="h-7"
									/>
								</div>
								<!-- 引用上限 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title text-gray-700 dark:text-gray-300 mb-1 text-center">
										{$i18n.t('Models KnowledgeBase Use Limit')}
									</div>
									<input
										type="number"
										class="form-input-sm"
										bind:value={agent.params.knowledge.settings.useLimit}
									/>
								</div>
								<!-- 检索相关度 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title text-gray-700 dark:text-gray-300 mb-1 text-center">
										{$i18n.t('Models KnowledgeBase Relevance')}
									</div>
									<input
										type="number"
										class="form-input-sm"
										bind:value={agent.params.knowledge.settings.relevance}
									/>
								</div>
								<!-- 内容重排 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title text-gray-700 dark:text-gray-300 mb-1 text-center">
										{$i18n.t('Models KnowledgeBase Content Reordering')}
									</div>
									<div class="flex items-center gap-2">
                                        <Label.Root for="knowledgeContentReordering" class="text-xs font-medium dark:text-gray-300">
											{agent.params?.knowledge?.settings?.contentReordering ? $i18n.t('On') : $i18n.t('Off')}
									    </Label.Root>
										<Switch bind:state={agent.params.knowledge.settings.contentReordering} activeClass="bg-indigo-500" />
                                    </div>
								</div>
								<!-- 优化提问 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title text-gray-700 dark:text-gray-300 mb-1 text-center">
										{$i18n.t('Models KnowledgeBase Optimization')}
									</div>
									<div class="flex items-center gap-2">
                                        <Label.Root for="knowledgeOptimization" class="text-xs font-medium dark:text-gray-300">
											{agent.params?.knowledge?.settings?.optimization ? $i18n.t('On') : $i18n.t('Off')}
									    </Label.Root>
										<Switch bind:state={agent.params.knowledge.settings.optimization} activeClass="bg-indigo-500" />
                                    </div>
								</div>
							</div>
                            <hr class="form-divider mb-3" />
                            <div class="grid grid-cols-2 gap-3 text-xs">
                                {#each agent.params?.knowledge?.items ?? [] as item, index}
                                    <div class="item-card">
                                        <div class="item-card-content">
                                            <div class="item-badge">KB</div>
                                            <div class="item-card-title">
                                                {item}
                                            </div>
                                        </div>
                                        <button 
                                            class="item-delete-button" 
                                            on:click={() => removeKnowledgeItem(index)}
                                            aria-label="删除项目"
                                        >
                                            <Close />
                                        </button>
                                    </div>
                                {/each}
                            </div>
						</div>
                        <!-- 工具选择 -->
                        <div class="form-panel gradient-panel">
                            <div class="form-panel-header mb-3">
                                <div class="form-title text-gray-800 dark:text-gray-200">
                                    {$i18n.t('Models Tools')}
                                </div>
                                <button class="icon-button accent-button">
                                    <CirclePlus />
                                    <span class="text-xs">{$i18n.t('Add')}</span>
                                </button>
                            </div>
                            <hr class="form-divider mb-3" />
                            <div class="grid grid-cols-2 gap-3 text-xs">
                                {#each agent.params?.tools as tool, index}
                                    <div class="item-card">
                                        <div class="item-card-content">
                                            <div class="item-badge tool-badge">T</div>
                                            <div class="item-card-title">
                                                {tool}
                                            </div>
                                        </div>
                                        <button 
                                            class="item-delete-button" 
                                            on:click={() => removeTool(index)}
                                            aria-label="删除项目"
                                        >
                                            <Close />
                                        </button>
                                    </div>
                                {/each}
                            </div>
                        </div>
					</div>
				</div>
			</div>

			<div class="px-5 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex justify-between items-center rounded-b-lg">
                <button class="action-button action-button-delete" on:click={() => deleteConfirmDialogShow = true}>
                    {$i18n.t('Delete')}
                </button>
                <div class="flex gap-2">
                    <button class="action-button action-button-cancel" on:click={closeModal}>
                        {$i18n.t('Cancel')}
                    </button>
                    <button class="action-button action-button-save" on:click={confirmHandler}>
                        {$i18n.t('Save')}
                    </button>
                </div>
            </div>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		top: 0;
		right: 0;
		left: 0;
		bottom: 0;
		background-color: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(2px);
		width: 100%;
		height: 100vh;
		max-height: 100dvh;
		display: flex;
		justify-content: center;
		align-items: center; /* 垂直居中 */
		z-index: 99999999;
		overflow: hidden;
		overscroll-contain: contain;
	}

	.modal-content {
		animation: scaleUp 0.2s ease-out forwards;
		max-height: 90vh; /* 设置最大高度 */
		display: flex;
		flex-direction: column;
	}

	.modal-closing {
		animation: scaleDown 0.2s ease-out forwards;
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.form-group {
		display: flex;
		flex-direction: column;
	}

	.form-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.form-title {
		font-weight: 600;
	}

	.form-input {
		width: 100%;
		border-radius: 0.375rem;
		border: 1px solid #e2e8f0;
		padding: 0.5rem 0.75rem;
		background-color: #ffffff;
		font-size: 0.875rem;
		color: #1a202c;
		transition: all 0.2s;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}

	.form-input:focus, .form-textarea:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
	}

	.form-input-sm {
		width: 100%;
		max-width: 80px;
		border-radius: 0.375rem;
		border: 1px solid #e2e8f0;
		padding: 0.25rem 0.5rem;
		background-color: #ffffff;
		font-size: 0.75rem;
		color: #1a202c;
		text-align: center;
		transition: all 0.2s;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}
	
	.form-input-sm:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
	}

	.form-textarea {
		width: 100%;
		border-radius: 0.375rem;
		border: 1px solid #e2e8f0;
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		background-color: #ffffff;
		color: #1a202c;
		resize: vertical;
		min-height: 80px;
		transition: all 0.2s;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}

	.form-panel {
		display: flex;
		flex-direction: column;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		padding: 1rem;
		background-color: #f8fafc;
		transition: all 0.2s;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	}

	.gradient-panel {
		background: linear-gradient(to bottom, #f8fafc, #f1f5f9);
		border-top: 3px solid #818cf8;
	}

	.form-panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.form-divider {
		border: none;
		height: 1px;
		background-color: #e2e8f0;
		margin: 0;
	}

	.icon-button {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		color: #4b5563;
		background-color: #f3f4f6;
		border: 1px solid #e5e7eb;
		transition: all 0.2s;
	}

	.icon-button:hover {
		background-color: #e5e7eb;
		color: #1f2937;
	}

	.accent-button {
		color: #4f46e5;
		background-color: #e0e7ff;
		border-color: #c7d2fe;
	}
	
	.accent-button:hover {
		background-color: #c7d2fe;
		color: #4338ca;
	}

	.action-button {
		border-radius: 0.375rem;
		padding: 0.5rem 1rem;
		font-size: 0.875rem;
		font-weight: 500;
		transition: all 0.2s;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}

	.action-button-delete {
		border: 1px solid #ef4444;
		color: #ef4444;
		background-color: transparent;
	}
	
	.action-button-delete:hover {
		background-color: #ef4444;
		color: white;
	}

	.action-button-cancel {
		border: 1px solid #9ca3af;
		color: #6b7280;
		background-color: transparent;
	}
	
	.action-button-cancel:hover {
		background-color: #9ca3af;
		color: white;
	}

	.action-button-save {
		border: 1px solid #4f46e5;
		color: white;
		background-color: #4f46e5;
		background-image: linear-gradient(to right, #4f46e5, #6366f1);
	}
	
	.action-button-save:hover {
		background-color: #4338ca;
		border-color: #4338ca;
		background-image: linear-gradient(to right, #4338ca, #4f46e5);
	}

	.item-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 0.75rem;
		background-color: white;
		border-radius: 0.375rem;
		border: 1px solid #e5e7eb;
		transition: all 0.2s;
	}

	.item-card:hover {
		border-color: #d1d5db;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		transform: translateY(-1px);
	}

	.item-card-content {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-grow: 1;
		overflow: hidden;
	}

	.item-badge {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 22px;
		min-width: 22px;
		border-radius: 4px;
		background-color: #e0e7ff;
		color: #4f46e5;
		font-weight: 600;
		font-size: 0.7rem;
	}

	.tool-badge {
		background-color: #fae8ff;
		color: #a855f7;
	}

	.item-card-title {
		font-weight: 500;
		color: #374151;
		text-overflow: ellipsis;
		overflow: hidden;
		white-space: nowrap;
	}

	.item-delete-button {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 20px;
		width: 20px;
		border-radius: 50%;
		color: #9ca3af;
		transition: all 0.2s;
	}
	
	.item-delete-button:hover {
		color: #ef4444;
		background-color: #fee2e2;
	}

	@keyframes scaleUp {
		from {
			transform: scale(0.985);
			opacity: 0;
		}
		to {
			transform: scale(1);
			opacity: 1;
		}
	}

	@keyframes scaleDown {
		from {
			transform: scale(1);
			opacity: 1;
		}
		to {
			transform: scale(0.985);
			opacity: 0;
		}
	}

	/* 暗黑模式支持 */
	:global(.dark) .form-input,
	:global(.dark) .form-textarea,
	:global(.dark) .form-input-sm {
		background-color: #1f2937;
		border-color: #374151;
		color: #e5e7eb;
	}

	:global(.dark) .form-input:focus,
	:global(.dark) .form-textarea:focus,
	:global(.dark) .form-input-sm:focus {
		border-color: #6366f1;
		box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.3);
	}

	:global(.dark) .form-panel {
		background-color: #111827;
		border-color: #374151;
	}
	
	:global(.dark) .gradient-panel {
		background: linear-gradient(to bottom, #111827, #0f172a);
		border-top: 3px solid #6366f1;
	}

	:global(.dark) .form-divider {
		background-color: #374151;
	}

	:global(.dark) .icon-button {
		background-color: #1f2937;
		border-color: #374151;
		color: #d1d5db;
	}

	:global(.dark) .icon-button:hover {
		background-color: #374151;
		color: #f3f4f6;
	}
	
	:global(.dark) .accent-button {
		color: #a5b4fc;
		background-color: rgba(99, 102, 241, 0.2);
		border-color: rgba(99, 102, 241, 0.3);
	}
	
	:global(.dark) .accent-button:hover {
		background-color: rgba(99, 102, 241, 0.3);
		color: #c7d2fe;
	}

	:global(.dark) .item-card {
		background-color: #1f2937;
		border-color: #374151;
	}

	:global(.dark) .item-card:hover {
		border-color: #4b5563;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
	}

	:global(.dark) .item-card-title {
		color: #e5e7eb;
	}
	
	:global(.dark) .item-badge {
		background-color: rgba(99, 102, 241, 0.2);
		color: #a5b4fc;
	}
	
	:global(.dark) .tool-badge {
		background-color: rgba(168, 85, 247, 0.2);
		color: #d8b4fe;
	}

	:global(.dark) .item-delete-button {
		color: #6b7280;
	}

	:global(.dark) .item-delete-button:hover {
		color: #ef4444;
		background-color: rgba(239, 68, 68, 0.15);
	}
	
	:global(.dark) .action-button-save {
		background-image: linear-gradient(to right, #4f46e5, #6366f1);
	}
	
	:global(.dark) .action-button-save:hover {
		background-image: linear-gradient(to right, #4338ca, #4f46e5);
	}
</style>
