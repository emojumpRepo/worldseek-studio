<script lang="ts">
    import ModelSettingDialog from './Models/ModelSettingDialog.svelte';
	import ModelCreateDialog from './Models/ModelCreateDialog.svelte';
	import { toast } from 'svelte-sonner';
    import type { Agent } from '$lib/types';
	import { onMount, getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, mobile, models as _models, settings, user } from '$lib/stores';
	import {
		deleteModelById,
		getModels as getWorkspaceModels,
		updateModelById,
		createNewModel
	} from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import { getGroups } from '$lib/apis/groups';
	import Spinner from '../common/Spinner.svelte';
	import { eventBus } from '$lib/stores';

	let shiftKey = false;
	let loaded = false;

    let selectedAgent: Agent = {
        id: '',
        name: '',
        description: '',
        access_control: {},
        base_app_id: '',
        user_id: '',
        params: {
            model: '',
            prompt: '',
            knowledge: {
                settings: {
                    searchMode: '',
                    useLimit: 0,
                    relevance: 0,
                    contentReordering: false,
                    optimization: false,
                },
                items: [],
            },
            tools: [],
        },
    }

	let models: Agent[] = [];

	let filteredModels: Agent[] = [];

	let showModelSettingDialog = false;
	let showModelCreateDialog = false;
	let group_ids: string[] = [];

	$: if (models) {
		filteredModels = models.filter(
			(m) => searchValue === '' || m.name.toLowerCase().includes(searchValue.toLowerCase())
		);
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

		await _models.set(
			await getModels(localStorage.token)
		);
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

		await _models.set(
			await getModels(localStorage.token)
		);
		models = await getWorkspaceModels(localStorage.token);
    }

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

		await _models.set(
			await getModels(localStorage.token)
		);
		models = await getWorkspaceModels(localStorage.token);
    }

	onMount(async () => {
		models = await getWorkspaceModels(localStorage.token);
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
		eventBus.update(bus => ({ ...bus, showCreateDialog: false }));
	}
    
    // 直接打开创建弹窗
    const openCreateDialog = () => {
        console.log('直接打开创建弹窗');
        showModelCreateDialog = true;
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

	<ModelCreateDialog
		bind:show={showModelCreateDialog}
        on:confirm={createModelHandler}
	/>

    <div class="my-4 mb-5">
        <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">智能体列表</h2>
            <button 
                class="flex items-center gap-1 py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                on:click={openCreateDialog}
            >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
                </svg>
                新建智能体
            </button>
        </div>
        <div class="gap-4 grid lg:grid-cols-2 xl:grid-cols-3" id="model-list">
            {#each filteredModels as model}
                <div class="agent-card">
                    <div class="agent-header">
                        <div class="agent-avatar">
                            <span class="agent-initial">{model.name.charAt(0)}</span>
                        </div>
                        <div class="agent-info">
                            <h3 class="agent-name">{model.name}</h3>
                            <div class="agent-mode {model.access_control ? 'mode-private' : 'mode-public'}">
                                {#if model.access_control}
                                    <svg xmlns="http://www.w3.org/2000/svg" class="mode-icon" viewBox="0 0 20 20" fill="currentColor">
                                        <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
                                    </svg>
                                    <span>私有模式</span>
                                {:else}
                                    <svg xmlns="http://www.w3.org/2000/svg" class="mode-icon" viewBox="0 0 20 20" fill="currentColor">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM4.332 8.027a6.012 6.012 0 011.912-2.706C6.512 5.73 6.974 6 7.5 6A1.5 1.5 0 019 7.5V8a2 2 0 004 0 2 2 0 011.523-1.943A5.977 5.977 0 0110 2c-1.61 0-3.09.62-4.19 1.64a.75.75 0 010 1.06A5.99 5.99 0 0111 5.3c.3 0 .58.02.86.05.03.3.05.6.05.9V8a3 3 0 01-6 0V7.5a.5.5 0 00-1 0V8a4 4 0 108 0c0-.17-.01-.33-.03-.49a6 6 0 01-9.65 6.11.75.75 0 010-1.06A5.99 5.99 0 0110 14c.34 0 .67-.03 1-.1V10a.75.75 0 000-1.5v3.73c.84-.31 1.63-.84 2.27-1.57a.75.75 0 10-1.38-.91 4.62 4.62 0 01-3.89 2.2c-1.25 0-2.41-.5-3.3-1.29a.75.75 0 00-1.06 0A5.972 5.972 0 0110 18c3.31 0 6-2.69 6-6 0-.32-.03-.63-.08-.93a.748.748 0 00-.26-1.08c-.13-.09-.27-.16-.42-.21h-.01V8a3 3 0 00-3-3 3 3 0 00-3 3 .5.5 0 01-1 0z" clip-rule="evenodd" />
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
                        <button 
                            class="agent-action-btn"
                            on:click={() => {
                                showModelSettingDialog = true;
                                selectedAgent = model;
                            }}
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            设置
                        </button>
                    </div>
                </div>
            {/each}
        </div>
    </div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}

<style>
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
    }

    .agent-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
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
        background-color: #ECFDF5;
        border: 1px solid #A7F3D0;
    }

    .mode-private {
        color: #7C3AED;
        background-color: #F5F3FF;
        border: 1px solid #DDD6FE;
    }

    :global(.dark) .mode-public {
        color: #10B981;
        background-color: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.2);
    }

    :global(.dark) .mode-private {
        color: #A78BFA;
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
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .agent-footer {
        display: flex;
        justify-content: flex-end;
        margin-top: auto;
        padding-top: 12px;
        border-top: 1px solid #f3f4f6;
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

    @media (prefers-color-scheme: dark) {
        .agent-card {
            background-color: #1f2937;
            border-color: #374151;
        }
        
        .agent-card:hover {
            border-color: #3b82f6;
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
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
    }
</style>
