<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { fade } from 'svelte/transition';
	import { Label, RadioGroup } from 'bits-ui';
	import Close from '$lib/components/icons/Close.svelte';
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
		access_control: {}
	};
	
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
		padding: 0.15rem 0.5rem;
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
