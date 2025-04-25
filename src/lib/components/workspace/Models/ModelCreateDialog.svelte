<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { fade } from 'svelte/transition';
    import { toast } from 'svelte-sonner';
	import Close from '$lib/components/icons/Close.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import type { Agent, WorkflowApp } from '$lib/types';
	import { createNewModel, getWorkflowApps } from '$lib/apis/models';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let modalElement: HTMLElement | null = null;
	let mounted = false;
	let isClosing = false;

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

	// 获取所有可选应用
	const getAllWorkflowApps = async () => {
		getWorkflowApps(localStorage.token).then((res) => {
			if (res.data) {
				workflowApps = res.data;
			}
		});
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
					{$i18n.t('Model Create')}
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
			<div class="p-3 flex-1">
				<div class="flex flex-col gap-4 text-sm">
					<!-- 智能体名称 表单项 -->
					<div class="form-group">
						<div class="form-header">
							<div class="form-title">
								{$i18n.t('Model Name')}
							</div>
						</div>
						<input
							type="text"
							class="form-input"
							bind:value={name}
							placeholder={$i18n.t('Model Name Placeholder')}
						/>
					</div>

					<!-- 可选应用 表单项 -->
					<div class="form-group flex-1">
						<div class="form-title">
							{$i18n.t('Model APP Choice')}
						</div>
						<div class="grid grid-cols-2 gap-2 flex-1 overflow-y-auto">
							{#each workflowApps as workflowApp}
								<div
									class="rounded-lg p-3 cursor-pointer hover:shadow-md transition-all duration-200 {selectedWorkflowApp?.id ===
									workflowApp.id
										? 'bg-[#414141] text-white'
										: 'bg-[#f0f0f0] text-black'}"
									on:click={() => {
										selectedWorkflowApp = workflowApp;
										name = workflowApp.name;
									}}
								>
									<div class="text-sm font-semibold">{workflowApp.name}</div>
									<div class="text-xs mt-1">{workflowApp.description}</div>
								</div>
							{/each}
						</div>
					</div>
				</div>
			</div>

			<div class="p-3 mt-0 flex justify-between items-center">
				<button class="action-button action-button-cancel" on:click={closeModal}>
					{$i18n.t('Cancel')}
				</button>
				<button class="action-button action-button-save" on:click={confirmHandler}>
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
		gap: 0.5rem;
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
