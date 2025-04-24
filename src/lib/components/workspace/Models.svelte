<script lang="ts">
    import ModelSettingDialog from './Models/ModelSettingDialog.svelte';
	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, mobile, models as _models, settings, user } from '$lib/stores';
	import {
		createNewModel,
		deleteModelById,
		getModels as getWorkspaceModels,
		toggleModelById,
		updateModelById
	} from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import { getGroups } from '$lib/apis/groups';
	import Spinner from '../common/Spinner.svelte';

	let shiftKey = false;
	let loaded = false;

    let selectedAgent = {
        name: '',
        description: '',
        params: {},
        access_control: {},
    }

	let models = [];

	let filteredModels = [];

	let showModelSettingDialog = true;

	let group_ids = [];

	$: if (models) {
		filteredModels = models.filter(
			(m) => searchValue === '' || m.name.toLowerCase().includes(searchValue.toLowerCase())
		);
		console.log('filteredModels', filteredModels);
	}

	let searchValue = '';

	const deleteModelHandler = async (model) => {
		const res = await deleteModelById(localStorage.token, model.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: model.id }));
		}

		await _models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
		models = await getWorkspaceModels(localStorage.token);
	};

	onMount(async () => {
		models = await getWorkspaceModels(localStorage.token);
		console.log('models', models);
		let groups = await getGroups(localStorage.token);
		group_ids = groups.map((group) => group.id);

		loaded = true;

		const onKeyDown = (event) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event) => {
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
	/>

    <div class="my-4 mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3" id="model-list">
        {#each filteredModels as model}
            <div class="flex flex-col w-full px-5 pt-4 pb-2 gap-3 rounded-lg transition hover:shadow-lg border-2 border-solid border-[#e6ebf0]">
                <div class="flex items-center gap-3">
                    <img class="rounded-full w-10 h-10" src='/static/favicon.png' alt="model profile" />
                    <div class="text-base font-bold text-black">
                        {model.name}
                    </div>
                </div>
                <div class="text-sm line-clamp-3 text-[#596275] leading-7">
                    {model.description}
                </div>
                <div class="flex items-center justify-between">
                    <div class="font-bold text-[#465064]">
                        {model.access_control ? '私有模式' : '公开模式'}
                    </div>
                    <button class="text-sm text-[#fff] px-2 py-1 rounded-md bg-[#465064]" on:click={() => {
                        showModelSettingDialog = true;
                        selectedAgent = model;
                    }}>
                        设置
                    </button>
                </div>
            </div>
        {/each}
    </div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
