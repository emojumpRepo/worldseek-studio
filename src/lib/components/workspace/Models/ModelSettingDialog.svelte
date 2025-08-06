<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { fade } from 'svelte/transition';
	import { Label, RadioGroup, Checkbox } from 'bits-ui';
	import Close from '$lib/components/icons/Close.svelte';
    import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { getFastGPTKnowledgeBases } from '$lib/apis';
	import type { Agent } from '$lib/types';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let agent: Agent = {
		id: '',
		name: '',
		description: '',
		base_app_id: '',
		user_id: '',
		access_control: {}
	};
	
	// 创建agent的本地副本用于编辑
	let localAgent: Agent = {...agent};
	let originalAgent: Agent = {...agent};
	
	// 初始化本地副本（首次显示时）
	let isFirstShow = true;
    $: if (show && isFirstShow) {
        isFirstShow = false;
        // 保存原始数据
        originalAgent = JSON.parse(JSON.stringify(agent));
        // 创建编辑副本
        localAgent = JSON.parse(JSON.stringify(agent));
        if (!localAgent.description) {
            localAgent.description = localAgent.workflow_app?.description || '';
        }
		// 加载知识库列表
		loadKnowledgeBases();
    }

	// 从localAgent.access_control派生accessControl值
	let accessControl = 'private';
	$: accessControl = localAgent.access_control ? 'private' : 'public';

	// 当RadioGroup选择变化时手动更新localAgent
	function handleAccessChange(value: string) {
		if (value === 'public') {
			localAgent.access_control = null;
		} else {
			localAgent.access_control = {};
		}
	}

	// 处理最大Tokens数量输入
	function handleLimitInput(e: Event) {
		const target = e.target as HTMLInputElement;
		const value = parseInt(target.value);
		if (!isNaN(value)) {
			if (value < 0) {
				knowledgeParams.limit = 0;
			} else if (value > 32000) {
				knowledgeParams.limit = 32000;
			} else {
				knowledgeParams.limit = value;
			}
		} else {
			knowledgeParams.limit = 4000;
		}
	}

	// 处理最低相关度输入
	function handleSimilarityInput(e: Event) {
		const target = e.target as HTMLInputElement;
		const value = parseFloat(target.value);
		if (!isNaN(value)) {
			if (value < 0) {
				knowledgeParams.similarity = 0;
			} else if (value > 1) {
				knowledgeParams.similarity = 1;
			} else {
				knowledgeParams.similarity = Math.round(value * 100) / 100; // 保留2位小数
			}
		} else {
			knowledgeParams.similarity = 0.1;
		}
	}

	// 知识库参数相关
	let selectedKnowledgeBases: string[] = [];
	let knowledgeParams = {
		datasetIds: [] as string[],
		limit: 4000,
		similarity: 0.1 as number | null,
		searchMode: 'embedding',
		usingReRank: false,
		datasetSearchUsingExtensionQuery: false,
		datasetSearchExtensionBg: ''
	};

	let isInitialized = false;
	
	// 初始化知识库参数
	$: if (show && !isInitialized) {
		let params = null;
		
		// 如果 localAgent.params 为 null，设置默认值
		if (localAgent.params === null || localAgent.params === undefined) {
			params = {
				knowledgeBases: [],
				datasetIds: [],
				limit: 4000,
				similarity: 0.1,
				searchMode: 'embedding',
				usingReRank: false,
				datasetSearchUsingExtensionQuery: false,
				datasetSearchExtensionBg: ''
			};
		} else {
			// 如果params是字符串，解析为对象；如果已经是对象，直接使用
			params = typeof localAgent.params === 'string' ? JSON.parse(localAgent.params) : localAgent.params;
		}
		
		if (params) {
			selectedKnowledgeBases = params.knowledgeBases || params.datasetIds || [];
			knowledgeParams = {
				datasetIds: params.datasetIds || params.knowledgeBases || [],
				limit: params.limit || 4000,
				similarity: params.similarity || 0.1,
				searchMode: params.searchMode || 'embedding',
				usingReRank: params.usingReRank || false,
				datasetSearchUsingExtensionQuery: params.datasetSearchUsingExtensionQuery || false,
				datasetSearchExtensionBg: params.datasetSearchExtensionBg || ''
			};
		}
		isInitialized = true;
	}

	// 知识库列表数据
	let knowledgeList: Array<{
		id: string;
		name: string;
		description: string;
		avatar?: string;
		vectorModel?: Record<string, any>;
		tags?: string[];
		createTime?: string;
		updateTime?: string;
		type?: string;
		status?: string;
	}> = [];
	let loadingKnowledgeBases = false;
	let knowledgeBasesError = '';

	// 加载FastGPT知识库列表
	const loadKnowledgeBases = async () => {
		if (!show) return;

		loadingKnowledgeBases = true;
		knowledgeBasesError = '';
		
		try {
			const token = localStorage.getItem('token');
			if (!token) {
				throw new Error('未找到认证令牌');
			}

			const response = await getFastGPTKnowledgeBases(token);
			if (response && Array.isArray(response)) {
				knowledgeList = response;
				
				// 验证当前选中的知识库ID是否仍然有效，移除无效的ID
				if (selectedKnowledgeBases.length > 0) {
					const validKnowledgeBaseIds = new Set(knowledgeList.map(kb => kb.id));
					const originalSelectedCount = selectedKnowledgeBases.length;
					const validatedSelectedKnowledgeBases = selectedKnowledgeBases.filter(id => 
						validKnowledgeBaseIds.has(id)
					);
					
					if (validatedSelectedKnowledgeBases.length !== originalSelectedCount) {
						selectedKnowledgeBases = validatedSelectedKnowledgeBases;
						const removedCount = originalSelectedCount - validatedSelectedKnowledgeBases.length;
						console.warn(`智能体设置初始化时已移除 ${removedCount} 个无效的知识库ID`);
					}
				}
			} else {
				knowledgeList = [];
				
				// 知识库列表为空时，清空选中的知识库ID
				if (selectedKnowledgeBases.length > 0) {
					console.warn('知识库列表为空，已清空选中的知识库');
					selectedKnowledgeBases = [];
				}
			}
		} catch (error) {
			console.error('加载知识库列表失败:', error);
			knowledgeBasesError = typeof error === 'string' 
				? error 
				: (error as any)?.message || '加载知识库列表失败';
			knowledgeList = [];
		} finally {
			loadingKnowledgeBases = false;
		}
	};

	// 同步 selectedKnowledgeBases 和 datasetIds
	$: if (knowledgeParams && selectedKnowledgeBases) {
		knowledgeParams.datasetIds = [...selectedKnowledgeBases];
	}

	let modalElement: HTMLElement | null = null;
	let mounted = false;
	let isClosing = false;
	let deleteConfirmDialogShow = false;

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			closeModal();
		}
	};

	// 关闭弹窗（取消操作）
	const closeModal = () => {
		if (isClosing) return;
		isClosing = true;
		// 恢复原始数据（取消修改）
		Object.assign(agent, originalAgent);
		setTimeout(() => {
			isClosing = false;
			show = false;
			isFirstShow = true; // 重置标志，以便下次打开弹窗时再次设置默认描述
			isInitialized = false; // 重置初始化标志，以便下次打开时重新初始化知识库参数
		}, 200); // 动画持续时间
	};

    // 保存智能体设置
	const confirmHandler = async () => {
        // 如果描述信息为空，则设置为官方应用的描述信息
        if(!localAgent.description) {
            localAgent.description = localAgent.workflow_app?.description || '';
        }
        
        // 验证知识库ID的有效性，移除不存在的知识库ID
        const validKnowledgeBaseIds = new Set(knowledgeList.map(kb => kb.id));
        const originalSelectedCount = selectedKnowledgeBases.length;
        const validatedSelectedKnowledgeBases = selectedKnowledgeBases.filter(id => 
            validKnowledgeBaseIds.has(id)
        );
        
        // 如果有无效的知识库ID被移除，更新选中状态
        if (validatedSelectedKnowledgeBases.length !== originalSelectedCount) {
            selectedKnowledgeBases = validatedSelectedKnowledgeBases;
            const removedCount = originalSelectedCount - validatedSelectedKnowledgeBases.length;
            console.warn(`已移除 ${removedCount} 个无效的知识库ID`);
        }
        
        // 保存知识库参数到params字段
        const params = {
            ...knowledgeParams,
            datasetIds: validatedSelectedKnowledgeBases // 使用验证后的知识库ID列表
        };
        localAgent.params = params;
        
        // 将localAgent的修改应用到原始agent
        Object.assign(agent, localAgent);
		console.log('agent', agent);
        
        dispatch('confirm', agent);
	};

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
							bind:value={localAgent.name}
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
							bind:value={localAgent.description}
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
									class="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-400 dark:hover:border-gray-500 data-[state=checked]:border-4 data-[state=checked]:border-black size-5 shrink-0 cursor-pointer rounded-full border transition-all duration-100 ease-in-out"
								/>
								<Label.Root for="private" class="pl-3 text-sm cursor-pointer"
									>{$i18n.t('Models Access Private')}</Label.Root
								>
							</div>
							<div class="text-gray-700 dark:text-gray-300 group flex select-none items-center transition-all">
								<RadioGroup.Item
									id="public"
									value="public"
									class="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-400 dark:hover:border-gray-500 data-[state=checked]:border-4 data-[state=checked]:border-black size-5 shrink-0 cursor-pointer rounded-full border transition-all duration-100 ease-in-out"
								/>
								<Label.Root for="public" class="pl-3 text-sm cursor-pointer">{$i18n.t('Models Access Public')}</Label.Root>
							</div>
						</RadioGroup.Root>
					</div>

					<!-- 知识库配置 表单项 -->
					<div class="form-group p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-100 dark:border-gray-800 shadow-sm">
						<div class="form-title mb-3 text-gray-800 dark:text-gray-200">
							{$i18n.t('Models Knowledge Base')}
						</div>
							
						<!-- 知识库选择 -->
						<div class="mb-4">
							<div class="text-sm text-gray-700 dark:text-gray-300 mb-3">选择知识库</div>
							
							{#if loadingKnowledgeBases}
								<div class="flex justify-center py-8">
									<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
									<span class="ml-2 text-sm text-gray-600">加载知识库列表...</span>
								</div>
							{:else if knowledgeBasesError}
								<div class="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
									<div class="text-sm text-red-600 mb-2">
										{knowledgeBasesError}
									</div>
									<button 
										class="text-sm text-red-700 underline hover:no-underline"
										on:click={loadKnowledgeBases}
									>
										重试
									</button>
								</div>
							{:else if knowledgeList.length === 0}
								<div class="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
									<div class="text-sm text-gray-600">
										暂无可用的知识库
									</div>
								</div>
							{:else}
								<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
									{#each knowledgeList as knowledge (knowledge.id)}
										{@const isSelected = selectedKnowledgeBases.includes(knowledge.id)}
										<div 
											class="item-card cursor-pointer {isSelected ? 'selected' : ''}"
											on:click={() => {
												if (isSelected) {
													selectedKnowledgeBases = selectedKnowledgeBases.filter(id => id !== knowledge.id);
												} else {
													selectedKnowledgeBases = [...selectedKnowledgeBases, knowledge.id];
												}
											}}
										>
											<div class="item-card-content">
												<div class="item-badge">
													{#if isSelected}
														<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
															<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
														</svg>
													{:else}
														KB
													{/if}
												</div>
												<div class="flex-1">
													<div class="item-card-title">{knowledge.name}</div>
													<div class="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
														{knowledge.description || '暂无描述'}
													</div>
												</div>
											</div>
										</div>
									{/each}
								</div>
							{/if}
						</div>

						<!-- 参数配置 -->
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
							<!-- 最大 Tokens 数量 -->
							<div>
								<label for="knowledge-limit" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									{$i18n.t('Models KnowledgeBase Limit')}
								</label>
								<input
									id="knowledge-limit"
									type="number"
									class="form-input-sm w-full"
									bind:value={knowledgeParams.limit}
									placeholder={$i18n.t('Models KnowledgeBase Limit Placeholder')}
									min="100"
									max="32000"
									on:input={handleLimitInput}
								/>
							</div>

							<!-- 最低相关度 -->
							<div>
								<label for="knowledge-similarity" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									{$i18n.t('Models KnowledgeBase Similarity')}
								</label>
								<input
									id="knowledge-similarity"
									type="number"
									class="form-input-sm w-full"
									bind:value={knowledgeParams.similarity}
									placeholder={$i18n.t('Models KnowledgeBase Similarity Placeholder')}
									min="0"
									max="1"
									step="0.1"
									on:input={handleSimilarityInput}
								/>
							</div>
						</div>

						<!-- 搜索模式 -->
						<div class="mt-4">
							<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Models KnowledgeBase Search Mode')}
							</div>
							<RadioGroup.Root
								class="flex gap-4 font-medium"
								value={knowledgeParams.searchMode}
								onValueChange={(value) => {
									knowledgeParams.searchMode = value;
								}}
							>
								<div class="text-gray-700 dark:text-gray-300 group flex select-none items-center transition-all">
									<RadioGroup.Item
										id="embedding"
										value="embedding"
										class="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-400 dark:hover:border-gray-500 data-[state=checked]:border-4 data-[state=checked]:border-black size-4 shrink-0 cursor-pointer rounded-full border transition-all duration-100 ease-in-out"
									/>
									<Label.Root for="embedding" class="pl-2 text-sm cursor-pointer">
										{$i18n.t('Models KnowledgeBase Search Mode Embedding')}
									</Label.Root>
								</div>
								<div class="text-gray-700 dark:text-gray-300 group flex select-none items-center transition-all">
									<RadioGroup.Item
										id="fullTextRecall"
										value="fullTextRecall"
										class="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-400 dark:hover:border-gray-500 data-[state=checked]:border-4 data-[state=checked]:border-black size-4 shrink-0 cursor-pointer rounded-full border transition-all duration-100 ease-in-out"
									/>
									<Label.Root for="fullTextRecall" class="pl-2 text-sm cursor-pointer">
										{$i18n.t('Models KnowledgeBase Search Mode FullText')}
									</Label.Root>
								</div>
								<div class="text-gray-700 dark:text-gray-300 group flex select-none items-center transition-all">
									<RadioGroup.Item
										id="mixedRecall"
										value="mixedRecall"
										class="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-400 dark:hover:border-gray-500 data-[state=checked]:border-4 data-[state=checked]:border-black size-4 shrink-0 cursor-pointer rounded-full border transition-all duration-100 ease-in-out"
									/>
									<Label.Root for="mixedRecall" class="pl-2 text-sm cursor-pointer">
										{$i18n.t('Models KnowledgeBase Search Mode Mixed')}
									</Label.Root>
								</div>
							</RadioGroup.Root>
						</div>

						<!-- 高级选项 -->
						<div class="mt-4 space-y-3">
							<!-- 使用重排 -->
							<div class="flex items-center gap-2">
								<Checkbox.Root
									id="usingReRank"
									class="size-4 shrink-0 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 data-[state=checked]:bg-black data-[state=checked]:border-black"
									checked={knowledgeParams.usingReRank}
									onCheckedChange={(checked) => {
										knowledgeParams.usingReRank = !!checked;
									}}
								>
									<Checkbox.Indicator class="flex items-center justify-center text-white">
										<svg class="size-3" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
										</svg>
									</Checkbox.Indicator>
								</Checkbox.Root>
								<Label.Root for="usingReRank" class="text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
									{$i18n.t('Models KnowledgeBase Content Reordering')}
								</Label.Root>
							</div>

							<!-- 使用问题优化 -->
							<div class="flex items-center gap-2">
								<Checkbox.Root
									id="datasetSearchUsingExtensionQuery"
									class="size-4 shrink-0 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 data-[state=checked]:bg-black data-[state=checked]:border-black"
									checked={knowledgeParams.datasetSearchUsingExtensionQuery}
									onCheckedChange={(checked) => {
										knowledgeParams.datasetSearchUsingExtensionQuery = !!checked;
									}}
								>
									<Checkbox.Indicator class="flex items-center justify-center text-white">
										<svg class="size-3" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
										</svg>
									</Checkbox.Indicator>
								</Checkbox.Root>
								<Label.Root for="datasetSearchUsingExtensionQuery" class="text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
									{$i18n.t('Models KnowledgeBase Optimization')}
								</Label.Root>
							</div>
						</div>

						<!-- 问题优化背景描述 -->
						{#if knowledgeParams.datasetSearchUsingExtensionQuery}
							<div class="mt-4">
								<label for="knowledge-background" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									{$i18n.t('Models KnowledgeBase Background Description')}
								</label>
								<textarea
									id="knowledge-background"
									class="form-input w-full"
									bind:value={knowledgeParams.datasetSearchExtensionBg}
									placeholder={$i18n.t('Models KnowledgeBase Background Placeholder')}
									rows={2}
								/>
							</div>
						{/if}
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
                    <button class="action-button btn-primary" on:click={confirmHandler}>
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
		border-radius: 0.375rem;
		border: 1px solid #e2e8f0;
		padding: 0.5rem 0.75rem;
		background-color: #ffffff;
		font-size: 0.875rem;
		color: #1a202c;
		text-align: left;
		transition: all 0.2s;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}
	
	.form-input-sm:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
	}

	/* 默认隐藏数字输入框的增减按钮 */
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}

	input[type="number"] {
		-moz-appearance: textfield; /* Firefox */
	}

	/* 为最低相关度输入框显示增减按钮 */
	#knowledge-similarity::-webkit-outer-spin-button,
	#knowledge-similarity::-webkit-inner-spin-button {
		-webkit-appearance: auto;
		margin: 0;
	}

	#knowledge-similarity[type="number"] {
		-moz-appearance: auto; /* Firefox */
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
		border: 1px solid #000000;
		color: #000000;
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

	.item-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 0.5rem;
		border-radius: 0.75rem;
		border: 1px solid #e5e7eb;
		background-color: #ffffff;
		min-height: 2.5rem;
		transition: all 0.2s ease;
		cursor: pointer;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	}

	.item-card:hover {
		border-color: #818cf8;
		background-color: #f8fafc;
		transform: translateY(-1px);
		box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.1), 0 2px 4px -1px rgba(99, 102, 241, 0.06);
	}

	.item-card.selected {
		border-color: #818cf8;
		/* background-color: #eef2ff; */
		box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.2);
	}

	.item-card-content {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex: 1;
	}

	.item-badge {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.75rem;
		height: 1.75rem;
		border-radius: 0.5rem;
		font-size: 0.75rem;
		font-weight: 600;
		background-color: #f1f5f9;
		color: #64748b;
		transition: all 0.2s ease;
	}

	.item-card.selected .item-badge {
		background-color: #818cf8;
		color: #ffffff;
	}

	.item-card-title {
		font-size: 0.875rem;
		font-weight: 500;
		color: #475569;
		transition: all 0.2s ease;
	}

	.item-card.selected .item-card-title {
		color: #4f46e5;
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
		background-color: #1e293b;
		border-color: #334155;
	}

	:global(.dark) .item-card:hover {
		border-color: #818cf8;
		background-color: #1e293b;
	}

	:global(.dark) .item-card.selected {
		border-color: #818cf8;
		background-color: rgba(99, 102, 241, 0.15);
	}

	:global(.dark) .item-badge {
		background-color: #334155;
		color: #94a3b8;
	}

	:global(.dark) .item-card.selected .item-badge {
		background-color: #818cf8;
		color: #ffffff;
	}

	:global(.dark) .item-card-title {
		color: #e2e8f0;
	}

	:global(.dark) .item-card.selected .item-card-title {
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
