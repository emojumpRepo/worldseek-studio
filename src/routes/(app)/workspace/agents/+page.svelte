<script>
	import { onMount } from 'svelte';
	import { config, models, settings } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import Models from '$lib/components/workspace/Models.svelte';

	onMount(async () => {
		const res = await getModels(localStorage.token, $config?.features?.enable_direct_connections && ($settings?.directConnections ?? null));
        console.log('getModels', res);
		// await Promise.all([
		// 	(async () => {
		// 		models.set(
		// 			await getAgents(
		// 				localStorage.token,
		// 				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
		// 			)
		// 		);
		// 	})()
		// ]);
	});
</script>

{#if $models !== null}
	<Models />
{/if}
