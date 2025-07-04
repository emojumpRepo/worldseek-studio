<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { fade } from 'svelte/transition';
	import { toast } from 'svelte-sonner';
	import Close from '$lib/components/icons/Close.svelte';
	import type { WorkflowApp } from '$lib/types';
	import { getWorkflowApps } from '$lib/apis/models';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let modalElement: HTMLElement | null = null;
	let mounted = false;
	let isClosing = false;
	let isLoading = false;

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
		}, 200); // 动画持续时间
	};

	// 保存智能体设置
	const confirmHandler = async () => {
		if (!selectedWorkflowApp) {
			toast.error($i18n.t('Please select a workflow app'));
			return;
		}
		dispatch('confirm', {
			name: name || selectedWorkflowApp.name,
			description: selectedWorkflowApp.description,
			base_app_id: selectedWorkflowApp.id,
			params: selectedWorkflowApp.params,
			access_control: {}
		});
	};

	let workflowApps: WorkflowApp[] = [];
	let name = '';
	let selectedWorkflowApp: WorkflowApp | null = null;
	let errorMessage = '';

	// 获取所有可选应用
	const getAllWorkflowApps = async (sync: boolean = false) => {
		isLoading = true;

		// 如果是同步操作，不清空错误信息，保持当前状态
		if (!sync) {
			errorMessage = '';
		}

		try {
			const res = await getWorkflowApps(localStorage.token, sync);
			console.log('getWorkflowApps', res, 'sync:', sync);
			if (res.success && res.data) {
				workflowApps = res.data;
				// 如果是同步操作且成功，清空之前的错误信息
				if (sync) {
					errorMessage = '';
					toast.success('工作流数据同步成功');
				}
				dispatch('updateWorkflowApps');
			} else {
				const errorMsg = (res as any).error || '获取工作流失败';
				if (sync) {
					// 同步失败时只显示Toast，不影响现有列表
					toast.error(`同步失败: ${errorMsg}`);
				} else {
					// 普通获取失败时清空列表并显示错误
					workflowApps = [];
					errorMessage = errorMsg;
					toast.error(errorMsg);
				}
			}
		} catch (error) {
			const errorMsg = '网络连接失败，请检查网络';
			console.error('getAllWorkflowApps error:', error);

			if (sync) {
				// 同步失败时只显示Toast，不影响现有列表
				toast.error(`同步失败: ${errorMsg}`);
			} else {
				// 普通获取失败时清空列表并显示错误
				workflowApps = [];
				errorMessage = errorMsg;
				toast.error(errorMsg);
			}
		}
		isLoading = false;
	};

	onMount(async () => {
		await getAllWorkflowApps();
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
			class="modal-content m-auto rounded-xl max-w-full w-[40rem] mx-2 bg-gray-50 max-h-[90vh] shadow-3xl flex flex-col {isClosing
				? 'modal-closing'
				: ''}"
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<!-- 设置弹窗头部（标题和关闭按钮） -->
			<div class="modal-header p-4 border-b border-gray-200">
				<div class="text-lg font-semibold text-gray-800">
					{$i18n.t('Model Create')}
				</div>
				<button
					class="hover:bg-gray-200 rounded-full p-1 transition-colors duration-200"
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
				<div class="flex flex-col gap-6">
					<!-- 智能体名称 表单项 -->
					<div class="form-group">
						<div class="form-header mb-2">
							<div class="form-title text-sm">
								{$i18n.t('Model Name')}
							</div>
						</div>
						<input
							type="text"
							class="form-input focus:ring-2 focus:ring-blue-500 focus:outline-none transition-shadow duration-200"
							bind:value={name}
							placeholder={$i18n.t('Model Name Placeholder')}
						/>
					</div>
					{#if isLoading}
						<div class="flex items-center justify-center h-40">
							<Spinner className="w-10 h-10" />
						</div>
					{:else}
						<!-- 可选应用 表单项 -->
						<div class="form-group flex-1">
							<div class="flex items-center justify-between mb-2">
								<div class="form-title text-sm">
									{$i18n.t('Model APP Choice')}
								</div>
								<button
									class="text-xs px-2 py-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors flex items-center gap-1"
									on:click={() => getAllWorkflowApps(true)}
									disabled={isLoading}
								>
									<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
										></path>
									</svg>
									从WorldSeek Agent同步
								</button>
							</div>
							{#if workflowApps.length === 0}
								<div class="flex flex-col items-center justify-center h-32 gap-3">
									<div class="text-gray-400">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											class="h-10 w-10"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="1.5"
												d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
											/>
										</svg>
									</div>
									{#if errorMessage}
										<p class="text-red-500 text-base font-medium">{errorMessage}</p>
										<div class="flex gap-2">
											<button
												class="px-3 py-1.5 text-sm bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
												on:click={() => getAllWorkflowApps(false)}
											>
												重试
											</button>
										</div>
									{:else}
										<p class="text-gray-500 text-base font-medium">暂无应用</p>
									{/if}
								</div>
							{:else}
								<div
									class="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[50vh] overflow-y-auto pr-1 pb-1"
								>
									{#each workflowApps as workflowApp}
										<div
											class="app-card {selectedWorkflowApp?.id === workflowApp.id
												? 'app-card-selected'
												: ''}"
											on:click={() => {
												selectedWorkflowApp = workflowApp;
												name = workflowApp.name;
											}}
										>
											<div class="app-badge">
												<span class="app-initial">{workflowApp.name.charAt(0)}</span>
											</div>
											<div class="app-card-content">
												<div class="app-card-name">{workflowApp.name}</div>
												<div class="app-card-desc">{workflowApp.description}</div>
											</div>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>

			<div class="p-4 border-t border-gray-200 flex justify-end items-center gap-3">
				<button class="btn-cancel" on:click={closeModal}>
					{$i18n.t('Cancel')}
				</button>
				<button class="btn-create" on:click={confirmHandler} disabled={!selectedWorkflowApp || isLoading}>
					{$i18n.t('Create')}
				</button>
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
		color: #374151;
	}

	.form-input {
		width: 100%;
		border-radius: 0.5rem;
		border: 1px solid #e5e7eb;
		padding: 0.625rem 0.75rem;
		background-color: white;
	}

	.app-card {
		position: relative;
		border-radius: 10px;
		background-color: white;
		padding: 16px;
		cursor: pointer;
		transition: all 0.15s ease;
		display: flex;
		align-items: flex-start;
		gap: 14px;
		min-height: 100px;
		border: 1px solid transparent;
	}

	.app-card:hover {
		background-color: rgba(156, 207, 216, 0.1); /* 使用主题色的10%透明度版本 */
		transition: background-color 0.2s ease;
	}

	.app-card-selected {
		background-color: #edf5ff;
		border: 1px solid #3b82f6;
	}

	.app-badge {
		width: 36px;
		height: 36px;
		border-radius: 8px;
		background-color: #e0e7ff;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.app-card-selected .app-badge {
		background-color: #3b82f6;
	}

	.app-initial {
		font-weight: 600;
		font-size: 16px;
		color: #4f46e5;
	}

	.app-card-selected .app-initial {
		color: white;
	}

	.app-card-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding-top: 2px;
	}

	.app-card-name {
		font-weight: 600;
		font-size: 0.95rem;
		color: #111827;
	}

	.app-card-desc {
		font-size: 0.85rem;
		color: #6b7280;
		line-clamp: 2;
		-webkit-line-clamp: 2;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.btn-cancel {
		border-radius: 0.5rem;
		padding: 0.5rem 1rem;
		font-size: 0.875rem;
		font-weight: 500;
		border: 1px solid #d1d5db;
		background-color: white;
		color: #374151;
		transition: all 0.2s ease;
	}

	.btn-cancel:hover {
		background-color: #f3f4f6;
	}

	.btn-create {
		border-radius: 0.5rem;
		padding: 0.5rem 1.25rem;
		font-size: 0.875rem;
		font-weight: 500;
		color: white;
		background-color: #0a0a0a;
		transition: all 0.2s ease;
	}

	.btn-create:disabled {
		background-color: #6b6b6be8;
		border-color: #6b6b6be8;
		cursor: not-allowed;
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
