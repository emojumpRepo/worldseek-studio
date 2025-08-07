<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { fade } from 'svelte/transition';
	import { Label, RadioGroup, Checkbox } from 'bits-ui';
	import Close from '$lib/components/icons/Close.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { getFastGPTKnowledgeBases } from '$lib/apis';
	import { user } from '$lib/stores';
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
	let localAgent: Agent = { ...agent };
	let originalAgent: Agent = { ...agent };

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
		// 不再在此处直接调用，改为通过响应式语句调用
	}

	// 从localAgent.access_control派生accessControl值
	let accessControl = 'private';
	$: accessControl = localAgent.access_control ? 'private' : 'public';

	// Tab 切换状态
	let activeTab = 'searchMode';

	// 判断是否显示知识库配置
	$: showKnowledgeBaseConfig =
		typeof localAgent.workflow_app?.params === 'object' &&
		localAgent.workflow_app?.params !== null &&
		(localAgent.workflow_app.params as Record<string, any>).has_custom_knowledge_base === true;

	// 当显示知识库配置时，加载知识库列表
	$: if (show && showKnowledgeBaseConfig) {
		loadKnowledgeBases();
	}

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
			};
		} else {
			// 如果params是字符串，解析为对象；如果已经是对象，直接使用
			params =
				typeof localAgent.params === 'string' ? JSON.parse(localAgent.params) : localAgent.params;
		}

		if (params) {
			selectedKnowledgeBases = params.knowledgeBases || params.datasetIds || [];
			knowledgeParams = {
				datasetIds: params.datasetIds || params.knowledgeBases || [],
				limit: params.limit || 4000,
				similarity: params.similarity || 0.1,
				searchMode: params.searchMode || 'embedding',
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
		if (!show || !showKnowledgeBaseConfig) return;

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
					const validKnowledgeBaseIds = new Set(knowledgeList.map((kb) => kb.id));
					const originalSelectedCount = selectedKnowledgeBases.length;
					const validatedSelectedKnowledgeBases = selectedKnowledgeBases.filter((id) =>
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
			knowledgeBasesError =
				typeof error === 'string' ? error : (error as any)?.message || '加载知识库列表失败';
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
		if (!localAgent.description) {
			localAgent.description = localAgent.workflow_app?.description || '';
		}

		// 验证知识库ID的有效性，移除不存在的知识库ID
		const validKnowledgeBaseIds = new Set(knowledgeList.map((kb) => kb.id));
		const originalSelectedCount = selectedKnowledgeBases.length;
		const validatedSelectedKnowledgeBases = selectedKnowledgeBases.filter((id) =>
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
	title="删除智能体"
	message="确定删除该智能体吗？"
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
			<div
				class="modal-header px-5 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-900/70 dark:to-gray-800/70 rounded-t-lg"
			>
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
							<div class="text-gray-500 dark:text-gray-400 text-xs">
								{agent.workflow_app?.name || ''}
							</div>
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
					<div
						class="form-group p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-100 dark:border-gray-800 shadow-sm"
					>
						<div class="form-title mb-3 text-gray-800 dark:text-gray-200">
							{$i18n.t('Models Access')}
						</div>
						<RadioGroup.Root
							class="flex gap-6 font-medium"
							value={accessControl}
							onValueChange={handleAccessChange}
						>
							<div
								class="text-gray-700 dark:text-gray-300 group flex select-none items-center transition-all"
							>
								<RadioGroup.Item
									id="private"
									value="private"
									class="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-400 dark:hover:border-gray-500 data-[state=checked]:border-4 data-[state=checked]:border-black size-5 shrink-0 cursor-pointer rounded-full border transition-all duration-100 ease-in-out"
								/>
								<Label.Root for="private" class="pl-3 text-sm cursor-pointer"
									>{$i18n.t('Models Access Private')}</Label.Root
								>
							</div>
							<div
								class="text-gray-700 dark:text-gray-300 group flex select-none items-center transition-all"
							>
								<RadioGroup.Item
									id="public"
									value="public"
									class="border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-400 dark:hover:border-gray-500 data-[state=checked]:border-4 data-[state=checked]:border-black size-5 shrink-0 cursor-pointer rounded-full border transition-all duration-100 ease-in-out"
								/>
								<Label.Root for="public" class="pl-3 text-sm cursor-pointer"
									>{$i18n.t('Models Access Public')}</Label.Root
								>
							</div>
						</RadioGroup.Root>
					</div>

					<!-- 知识库配置 表单项 -->
					{#if showKnowledgeBaseConfig}
						<div>
							<div class="form-title mb-2 text-gray-800 dark:text-gray-200">
								{$i18n.t('Models Knowledge Base')}
							</div>
							<div
								class="form-group p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-100 dark:border-gray-800 shadow-sm"
							>
								<!-- 知识库选择 -->
								<div class="mb-4">
									<!-- 已选择的知识库标签 -->
									<div class="knowledge-tags-container mb-3">
										{#if selectedKnowledgeBases.length > 0}
											<div class="flex flex-wrap gap-2">
												{#each selectedKnowledgeBases as selectedId (selectedId)}
													{@const selectedKnowledge = knowledgeList.find(
														(kb) => kb.id === selectedId
													)}
													{#if selectedKnowledge}
														<div class="knowledge-tag">
															<span class="knowledge-tag-text">{selectedKnowledge.name}</span>
															<button
																class="knowledge-tag-close"
																on:click={() => {
																	selectedKnowledgeBases = selectedKnowledgeBases.filter(
																		(id) => id !== selectedId
																	);
																}}
															>
																<svg
																	class="w-4 h-4"
																	fill="none"
																	stroke="currentColor"
																	viewBox="0 0 24 24"
																>
																	<path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		stroke-width="2"
																		d="M6 18L18 6M6 6l12 12"
																	/>
																</svg>
															</button>
														</div>
													{/if}
												{/each}
											</div>
										{:else}
											<div class="text-xs text-gray-500 dark:text-gray-400 py-2">
												暂未选择知识库
											</div>
										{/if}
									</div>

									<!-- 分割线 -->
									<div class="h-px bg-gray-200 dark:bg-gray-700 my-4"></div>

									<!-- 知识库选择列表 -->
									<div class="knowledge-dropdown">
										{#if loadingKnowledgeBases}
											<div class="flex justify-center py-8">
												<div
													class="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"
												></div>
												<span class="ml-2 text-sm text-gray-600">加载中...</span>
											</div>
										{:else if knowledgeBasesError}
											<div class="p-4 text-center">
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
											<div class="p-4 text-center">
												<div class="text-sm text-gray-600">暂无可用的知识库</div>
											</div>
										{:else}
											<div class="knowledge-options max-h-48 overflow-y-auto">
												{#each knowledgeList.filter((kb) => !selectedKnowledgeBases.includes(kb.id)) as knowledge (knowledge.id)}
													<div
														class="knowledge-option"
														on:click={() => {
															selectedKnowledgeBases = [...selectedKnowledgeBases, knowledge.id];
														}}
													>
														<div class="knowledge-option-title">{knowledge.name}</div>
													</div>
												{/each}
												{#if knowledgeList.filter((kb) => !selectedKnowledgeBases.includes(kb.id)).length === 0}
													<div class="text-sm text-gray-600 dark:text-gray-400 text-center">
														所有知识库已被选择
													</div>
												{/if}
											</div>
										{/if}
									</div>
								</div>
							</div>
							<!-- Tab 导航 -->
							<div class="mt-4">
								<div class="flex border-b border-gray-200 dark:border-gray-700 justify-center">
									<button
										class="tab-button {activeTab === 'searchMode' ? 'active' : ''}"
										on:click={() => (activeTab = 'searchMode')}
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
											/>
										</svg>
										{$i18n.t('Models KnowledgeBase Search Mode')}
									</button>
									<button
										class="tab-button {activeTab === 'searchFilter' ? 'active' : ''}"
										on:click={() => (activeTab = 'searchFilter')}
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
											/>
										</svg>
										{$i18n.t('Models KnowledgeBase Search Filter')}
									</button>
								</div>

								<!-- Tab 内容 -->
								<div class="mt-4">
									{#if activeTab === 'searchMode'}
										<!-- 搜索模式 -->
										<div class="space-y-4">
											<div class="flex flex-col gap-3">
												<button
													class="search-mode-button {knowledgeParams.searchMode === 'embedding'
														? 'selected'
														: ''}"
													on:click={() => (knowledgeParams.searchMode = 'embedding')}
												>
													<div
														class="mode-indicator {knowledgeParams.searchMode === 'embedding'
															? 'selected'
															: ''}"
													></div>
													<div class="mode-content">
														<div class="mode-title">
															{$i18n.t('Models KnowledgeBase Search Mode Embedding')}
														</div>
														<div class="mode-description">使用向量进行文本相关性查询</div>
													</div>
												</button>
												<button
													class="search-mode-button {knowledgeParams.searchMode === 'fullTextRecall'
														? 'selected'
														: ''}"
													on:click={() => (knowledgeParams.searchMode = 'fullTextRecall')}
												>
													<div
														class="mode-indicator {knowledgeParams.searchMode === 'fullTextRecall'
															? 'selected'
															: ''}"
													></div>
													<div class="mode-content">
														<div class="mode-title">
															{$i18n.t('Models KnowledgeBase Search Mode FullText')}
														</div>
														<div class="mode-description">使用传统的全文检索方法搜索数据</div>
													</div>
												</button>
												<button
													class="search-mode-button {knowledgeParams.searchMode === 'mixedRecall'
														? 'selected'
														: ''}"
													on:click={() => (knowledgeParams.searchMode = 'mixedRecall')}
												>
													<div
														class="mode-indicator {knowledgeParams.searchMode === 'mixedRecall'
															? 'selected'
															: ''}"
													></div>
													<div class="mode-content">
														<div class="mode-title">
															{$i18n.t('Models KnowledgeBase Search Mode Mixed')}
														</div>
														<div class="mode-description">
															使用向量检索与全文检索的混合结果，使用 RRF 算法进行排序。
														</div>
													</div>
												</button>
											</div>
										</div>
									{:else if activeTab === 'searchFilter'}
										<!-- 搜索过滤 -->
										<div class="space-y-6">
											<!-- 引用上限 -->
											<div class="space-y-3">
												<div class="flex items-center gap-5">
													<label
														for="limit-slider-input"
														class="block text-sm font-medium text-gray-700 dark:text-gray-300"
													>
														引用上限
													</label>
													<div class="slider-container flex-1">
														<input
															type="range"
															class="slider"
															bind:value={knowledgeParams.limit}
															min="100"
															max="32000"
															step="100"
															on:input={handleLimitInput}
														/>
														<div class="slider-track-bg"></div>
													</div>
													<div class="flex items-center gap-2">
														<input
															id="limit-slider-input"
															type="number"
															class="slider-input"
															bind:value={knowledgeParams.limit}
															min="100"
															max="32000"
															on:input={handleLimitInput}
														/>
													</div>
												</div>
											</div>

											<!-- 最低相关度 -->
											<div class="space-y-3">
												<div class="flex items-center gap-5">
													<label
														for="similarity-slider-input"
														class="block text-sm font-medium text-gray-700 dark:text-gray-300 shrink-0"
													>
														最低相关度
													</label>
													<div class="slider-container">
														<input
															type="range"
															class="slider"
															bind:value={knowledgeParams.similarity}
															min="0"
															max="1"
															step="0.1"
															on:input={handleSimilarityInput}
														/>
														<div class="slider-track-bg"></div>
													</div>
													<div class="flex items-center gap-2">
														<input
															id="similarity-slider-input"
															type="number"
															class="slider-input"
															bind:value={knowledgeParams.similarity}
															min="0"
															max="1"
															step="0.1"
															on:input={handleSimilarityInput}
														/>
													</div>
												</div>
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>

			<div
				class="px-5 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex justify-between items-center rounded-b-lg"
			>
				<button
					class="action-button action-button-delete"
					on:click={() => (deleteConfirmDialogShow = true)}
				>
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
	}

	@keyframes scaleUp {
		from {
			opacity: 0;
			transform: scale(0.95);
		}
		to {
			opacity: 1;
			transform: scale(1);
		}
	}

	@keyframes scaleDown {
		from {
			opacity: 1;
			transform: scale(1);
		}
		to {
			opacity: 0;
			transform: scale(0.95);
		}
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

	.form-input:focus,
	.form-textarea:focus {
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

	input[type='number'] {
		appearance: textfield;
		-moz-appearance: textfield; /* Firefox */
	}

	/* 为最低相关度输入框显示增减按钮 */
	#knowledge-similarity::-webkit-outer-spin-button,
	#knowledge-similarity::-webkit-inner-spin-button {
		-webkit-appearance: auto;
		margin: 0;
	}

	#knowledge-similarity[type='number'] {
		appearance: auto;
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
		box-shadow:
			0 4px 6px -1px rgba(99, 102, 241, 0.1),
			0 2px 4px -1px rgba(99, 102, 241, 0.06);
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

	/* 知识库选择列表样式 - 限制为两行并支持滚动 */
	.knowledge-base-grid {
		max-height: 200px; /* 大约两行的高度 */
		overflow-y: auto;
		padding-right: 4px; /* 为滚动条留出空间 */
	}

	/* 滚动条样式 */
	.knowledge-base-grid::-webkit-scrollbar {
		width: 6px;
	}

	.knowledge-base-grid::-webkit-scrollbar-track {
		background: #f1f1f1;
		border-radius: 3px;
	}

	.knowledge-base-grid::-webkit-scrollbar-thumb {
		background: #c1c1c1;
		border-radius: 3px;
	}

	.knowledge-base-grid::-webkit-scrollbar-thumb:hover {
		background: #a8a8a8;
	}

	/* 暗黑模式滚动条样式 */
	:global(.dark) .knowledge-base-grid::-webkit-scrollbar-track {
		background: #374151;
	}

	:global(.dark) .knowledge-base-grid::-webkit-scrollbar-thumb {
		background: #6b7280;
	}

	:global(.dark) .knowledge-base-grid::-webkit-scrollbar-thumb:hover {
		background: #9ca3af;
	}

	/* Tab 按钮样式 */
	.tab-button {
		padding: 0.75rem 1.5rem;
		border: none;
		background: transparent;
		color: #6b7280;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		border-bottom: 2px solid transparent;
		transition: all 0.2s ease;
		position: relative;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.tab-button:hover {
		color: #374151;
		background-color: #f9fafb;
	}

	.tab-button.active {
		color: #000000;
		border-bottom-color: #000000;
		background-color: #f8fafc;
	}

	/* 暗黑模式 Tab 样式 */
	:global(.dark) .tab-button {
		color: #9ca3af;
	}

	:global(.dark) .tab-button:hover {
		color: #e5e7eb;
		background-color: #1f2937;
	}

	:global(.dark) .tab-button.active {
		color: #ffffff;
		border-bottom-color: #ffffff;
		background-color: #1e293b;
	}

	/* 滑动条样式 */
	.slider-input {
		width: 80px;
		padding: 0.375rem 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		background-color: #ffffff;
		font-size: 0.875rem;
		text-align: center;
		transition: all 0.2s ease;
	}

	.slider-input:focus {
		outline: none;
		border-color: #000000;
		box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
	}

	.slider-container {
		position: relative;
		width: 100%;
	}

	.slider {
		width: 100%;
		height: 6px;
		background: transparent;
		outline: none;
		border-radius: 3px;
		-webkit-appearance: none;
		-moz-appearance: none;
		appearance: none;
		cursor: pointer;
		position: relative;
		z-index: 2;
	}

	.slider-track-bg {
		position: absolute;
		top: 50%;
		left: 0;
		right: 0;
		height: 6px;
		background: #e5e7eb;
		border-radius: 3px;
		transform: translateY(-50%);
		z-index: 1;
	}

	/* Webkit滑动条样式 */
	.slider::-webkit-slider-track {
		width: 100%;
		height: 6px;
		background: transparent;
		border-radius: 3px;
	}

	.slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 18px;
		height: 18px;
		background: #000000;
		border-radius: 50%;
		cursor: pointer;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
		transition: all 0.2s ease;
	}

	.slider::-webkit-slider-thumb:hover {
		background: #333333;
		transform: scale(1.1);
		box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
	}

	/* Firefox滑动条样式 */
	.slider::-moz-range-track {
		width: 100%;
		height: 6px;
		background: transparent;
		border-radius: 3px;
		border: none;
	}

	.slider::-moz-range-thumb {
		width: 18px;
		height: 18px;
		background: #000000;
		border-radius: 50%;
		cursor: pointer;
		border: none;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
		transition: all 0.2s ease;
	}

	.slider::-moz-range-thumb:hover {
		background: #333333;
		transform: scale(1.1);
		box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
	}

	/* 暗黑模式滑动条样式 */
	:global(.dark) .slider-input {
		background-color: #1f2937;
		border-color: #374151;
		color: #e5e7eb;
	}

	:global(.dark) .slider-input:focus {
		border-color: #ffffff;
		box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.2);
	}

	:global(.dark) .slider-track-bg {
		background: #4b5563;
	}

	:global(.dark) .slider::-webkit-slider-thumb {
		background: #ffffff;
	}

	:global(.dark) .slider::-webkit-slider-thumb:hover {
		background: #e5e7eb;
		box-shadow: 0 4px 8px rgba(255, 255, 255, 0.4);
	}

	:global(.dark) .slider::-moz-range-thumb {
		background: #ffffff;
	}

	:global(.dark) .slider::-moz-range-thumb:hover {
		background: #e5e7eb;
		box-shadow: 0 4px 8px rgba(255, 255, 255, 0.4);
	}

	/* 搜索模式按钮样式 */
	.search-mode-button {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 1rem;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		background-color: #ffffff;
		transition: all 0.2s ease;
		cursor: pointer;
		text-align: left;
	}

	.search-mode-button:hover {
		border-color: #d1d5db;
		background-color: #f9fafb;
	}

	.search-mode-button.selected {
		border-color: #000000;
		background-color: #f8fafc;
		box-shadow: 0 0 0 1px #000000;
	}

	.mode-indicator {
		width: 16px;
		height: 16px;
		border: 2px solid #d1d5db;
		border-radius: 50%;
		flex-shrink: 0;
		margin-top: 2px;
		transition: all 0.2s ease;
	}

	.mode-indicator.selected {
		border-color: #000000;
		background-color: #000000;
		position: relative;
	}

	.mode-indicator.selected::after {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 6px;
		height: 6px;
		background-color: #ffffff;
		border-radius: 50%;
	}

	.mode-content {
		flex: 1;
	}

	.mode-title {
		font-weight: 500;
		font-size: 0.875rem;
		color: #1f2937;
		margin-bottom: 0.25rem;
	}

	.mode-description {
		font-size: 0.75rem;
		color: #6b7280;
		line-height: 1.4;
	}

	/* 暗黑模式搜索按钮样式 */
	:global(.dark) .search-mode-button {
		background-color: #1f2937;
		border-color: #374151;
	}

	:global(.dark) .search-mode-button:hover {
		border-color: #4b5563;
		background-color: #374151;
	}

	:global(.dark) .search-mode-button.selected {
		border-color: #ffffff;
		background-color: #374151;
		box-shadow: 0 0 0 1px #ffffff;
	}

	:global(.dark) .mode-indicator {
		border-color: #6b7280;
	}

	:global(.dark) .mode-indicator.selected {
		border-color: #ffffff;
		background-color: #ffffff;
	}

	:global(.dark) .mode-indicator.selected::after {
		background-color: #000000;
	}

	:global(.dark) .mode-title {
		color: #f3f4f6;
	}

	:global(.dark) .mode-description {
		color: #9ca3af;
	}

	/* 知识库标签样式 */
	.knowledge-tags-container {
		min-height: 2rem;
	}

	.knowledge-tag {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0.5rem 0.375rem 0.75rem;
		background-color: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 0.4rem;
		font-size: 0.875rem;
		color: #374151;
		transition: all 0.2s ease;
	}

	.knowledge-tag:hover {
		background-color: #e5e7eb;
		border-color: #d1d5db;
	}

	.knowledge-tag-text {
		font-weight: 500;
		white-space: nowrap;
		max-width: 120px;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.knowledge-tag-close {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.25rem;
		height: 1.25rem;
		border-radius: 50%;
		color: #6b7280;
		transition: all 0.2s ease;
		background: transparent;
		border: none;
		cursor: pointer;
	}

	.knowledge-tag-close:hover {
		background-color: #d1d5db;
		color: #374151;
	}

	/* 知识库选择器 */
	.knowledge-dropdown {
		overflow: hidden;
	}

	/* 知识库选项 */
	.knowledge-options {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.knowledge-option {
		padding: 0.5rem 0.75rem;
		cursor: pointer;
		transition: all 0.2s ease;
		border-radius: 0.4rem;
		background-color: #ffffff;
		border: 1px solid #e5e7eb;
	}

	.knowledge-option:hover {
		background-color: #f9fafb;
		border-color: #000000;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	.knowledge-option-title {
		font-size: 0.875rem;
		font-weight: 500;
		color: #1f2937;
	}

	/* 暗黑模式知识库标签样式 */
	:global(.dark) .knowledge-tag {
		background-color: #374151;
		border-color: #4b5563;
		color: #e5e7eb;
	}

	:global(.dark) .knowledge-tag:hover {
		background-color: #4b5563;
		border-color: #6b7280;
	}

	:global(.dark) .knowledge-tag-close {
		color: #9ca3af;
	}

	:global(.dark) .knowledge-tag-close:hover {
		background-color: #6b7280;
		color: #f3f4f6;
	}

	:global(.dark) .knowledge-dropdown {
		background-color: #1f2937;
		border-color: #374151;
	}

	:global(.dark) .knowledge-option {
		background-color: #1f2937;
		border-color: #374151;
	}

	:global(.dark) .knowledge-option:hover {
		background-color: #374151;
		border-color: #ffffff;
		box-shadow: 0 2px 4px rgba(255, 255, 255, 0.1);
	}

	:global(.dark) .knowledge-option-title {
		color: #f3f4f6;
	}
</style>
