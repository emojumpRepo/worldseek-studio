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
			console.log('Escape');
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
        console.log('agent', agent);
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
			class="modal-content m-auto rounded-lg max-w-full w-[35rem] mx-2 bg-gray-50 dark:bg-gray-950 max-h-[90vh] shadow-3xl flex flex-col {isClosing
				? 'modal-closing'
				: ''}"
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<!-- 设置弹窗头部（标题和关闭按钮） -->
			<div class="modal-header p-3">
				<div class="font-medium dark:text-gray-200">
					{$i18n.t('Model APP Settings')}
				</div>
				<button
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
			<div class="p-3 flex-1 overflow-y-auto">
				<div class="flex flex-col gap-4 text-sm">
					<!-- 智能体名称 表单项 -->
					<div class="form-group">
						<div class="form-header">
							<div class="form-title">
								{$i18n.t('Model Name')}
							</div>
							<div class="text-[#cccccc]">{agent.workflow_app?.name || ''}</div>
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
						<div class="form-title">
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
					<div class="form-header">
						<div class="form-title">
							{$i18n.t('Models Access')}
						</div>
						<RadioGroup.Root
							class="flex gap-6 font-bold"
							value={accessControl}
							onValueChange={handleAccessChange}
						>
							<div class="text-foreground group flex select-none items-center transition-all">
								<RadioGroup.Item
									id="private"
									value="private"
									class="border-border-input bg-background hover:border-dark-40 data-[state=checked]:border-6 data-[state=checked]:border-foreground size-5 shrink-0 cursor-default rounded-full border transition-all duration-100 ease-in-out"
								/>
								<Label.Root for="private" class="pl-3 text-sm"
									>{$i18n.t('Models Access Private')}</Label.Root
								>
							</div>
							<div class="text-foreground group flex select-none items-center transition-all">
								<RadioGroup.Item
									id="public"
									value="public"
									class="border-border-input bg-background hover:border-dark-40 data-[state=checked]:border-6 data-[state=checked]:border-foreground size-5 shrink-0 cursor-default rounded-full border transition-all duration-100 ease-in-out"
								/>
								<Label.Root for="public" class="pl-3 text-sm">{$i18n.t('Models Access Public')}</Label.Root>
							</div>
						</RadioGroup.Root>
					</div>

					<!-- 智能体入参 表单项 -->
					<div class="flex flex-col gap-3">
						<div class="form-title">
							{$i18n.t('Models Params')}
						</div>
						<!-- 模型选择 -->
						<div class="form-panel">
							<div class="form-panel-header">
								<div class="form-title">
									{$i18n.t('Models Model Choice')}
								</div>
								<button class="icon-button">
									<Cog6 />
									{$i18n.t('Settings')}
								</button>
							</div>
							<hr class="form-divider" />

							<DropdownSelect
								bind:value={agent.params.model}
								options={modelList}
								placeholder="请选择模型"
							/>
						</div>
						<!-- 提示词 -->
						<div class="form-panel">
							<div class="form-panel-header">
								<div class="form-title">
									{$i18n.t('Models Prompt')}
								</div>
							</div>
							<hr class="form-divider" />
							<textarea
								class="form-textarea"
								bind:value={agent.params.prompt}
								placeholder={$i18n.t('Models Prompt Placeholder')}
								rows={4}
							/>
						</div>
						<!-- 知识库选择 -->
						<div class="form-panel">
							<div class="form-panel-header">
								<div class="form-title">
									{$i18n.t('Models Knowledge Base')}
								</div>
								<div class="flex items-center gap-3">
									<button class="icon-button">
										<Cog6 />
										{$i18n.t('Settings')}
									</button>
									<button class="icon-button">
										<CirclePlus />
										{$i18n.t('Add')}
									</button>
								</div>
							</div>
							<div class="grid grid-cols-5 gap-8 text-xs">
								<!-- 搜索模式 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title">
										{$i18n.t('Models KnowledgeBase Search Mode')}
									</div>
									<DropdownSelect
										bind:value={agent.params.knowledge.settings.searchMode}
										options={searchModeList}
										isShowIcon={false}
										labelClass="text-xs"
										height="h-6"
									/>
								</div>
								<!-- 引用上限 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title">
										{$i18n.t('Models KnowledgeBase Use Limit')}
									</div>
									<input
										type="number"
										class="form-input bg-white"
										bind:value={agent.params.knowledge.settings.useLimit}
									/>
								</div>
								<!-- 检索相关度 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title">
										{$i18n.t('Models KnowledgeBase Relevance')}
									</div>
									<input
										type="number"
										class="form-input bg-white"
										bind:value={agent.params.knowledge.settings.relevance}
									/>
								</div>
								<!-- 内容重排 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title">
										{$i18n.t('Models KnowledgeBase Content Reordering')}
									</div>
									<div class="flex items-center gap-2">
                                        <Label.Root for="knowledgeContentReordering" class="text-xs font-medium">
											{agent.params?.knowledge?.settings?.contentReordering ? $i18n.t('On') : $i18n.t('Off')}
									    </Label.Root>
										<Switch bind:state={agent.params.knowledge.settings.contentReordering} activeClass="bg-blue-500" />
                                    </div>
								</div>
								<!-- 优化提问 -->
								<div class="flex flex-col gap-2 items-center">
									<div class="form-title">
										{$i18n.t('Models KnowledgeBase Optimization')}
									</div>
									<div class="flex items-center gap-2">
                                        <Label.Root for="knowledgeOptimization" class="text-xs font-medium">
											{agent.params?.knowledge?.settings?.optimization ? $i18n.t('On') : $i18n.t('Off')}
									    </Label.Root>
										<Switch bind:state={agent.params.knowledge.settings.optimization} activeClass="bg-blue-500" />
                                    </div>
								</div>
							</div>
                            <hr class="form-divider" />
                            <div class="grid grid-cols-2 gap-3 text-xs">
                                {#each agent.params?.knowledge?.items ?? [] as item, index}
                                    <div class="item-card">
                                        <div class="item-card-content">
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
                        <div class="form-panel">
                            <div class="form-panel-header">
                                <div class="form-title">
                                    {$i18n.t('Models Tools')}
                                </div>
                                <button class="icon-button">
                                    <CirclePlus />
                                    {$i18n.t('Add')}
                                </button>
                            </div>
                            <hr class="form-divider" />
                            <div class="grid grid-cols-2 gap-3 text-xs">
                                {#each agent.params?.tools as tool, index}
                                    <div class="item-card">
                                        <div class="item-card-content">
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

			<div class="p-3 mt-0 flex justify-between items-center">
                <button class="action-button action-button-delete" on:click={() => {
                    deleteConfirmDialogShow = true;
                }}>
                    {$i18n.t('Delete')}
                </button>
                <div class="flex items-center gap-3">
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
		gap: 0.25rem;
	}

	.form-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.form-title {
		font-weight: 700;
		color: black;
	}

	.form-input {
		width: 100%;
		border-radius: 0.375rem;
		border: 1px solid #cccccc;
		padding: 0.25rem 0.5rem;
	}

	.form-textarea {
		width: 100%;
		border-radius: 0.375rem;
		border: 1px solid #cccccc;
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		background-color: #fff;
	}

	.form-panel {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		border: 1px solid #cccccc;
		border-radius: 0.375rem;
		padding: 0.75rem;
		background-color: #ededed;
	}

	.form-panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.form-divider {
		border-top: 1px solid #cccccc;
	}

	.icon-button {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.action-button {
		border-radius: 0.375rem;
		border-width: 1px;
		padding: 0.25rem 1rem;
		font-size: 0.875rem;
		transition: all 0.2s;
	}

	.action-button-delete {
		border-color: #ef4444;
		color: #ef4444;
	}
	.action-button-delete:hover {
		background-color: #ef4444;
		color: white;
	}

	.action-button-cancel {
		border-color: #6b7280;
		color: #6b7280;
	}
	.action-button-cancel:hover {
		background-color: #6b7280;
		color: white;
	}

	.action-button-save {
		border-color: #000000;
		color: #000000;
	}
	.action-button-save:hover {
		background-color: #000000;
		color: white;
	}

	.item-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem;
		background-color: white;
		border-radius: 0.375rem;
		border: 1px solid #e5e7eb;
	}

	.item-card-content {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-grow: 1;
		overflow: hidden;
	}

	.item-card-title {
		font-weight: 700;
		color: black;
		text-overflow: ellipsis;
		overflow: hidden;
		white-space: nowrap;
	}

	.item-delete-button {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		transition: color 0.2s;
	}
	.item-delete-button:hover {
		color: #ef4444;
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
</style>
