<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		console.log($user);
		if ($user?.role !== 'admin') {
			if ($user?.permissions?.workspace?.models) {
				goto('/workspace/agents');
			} else if ($user?.permissions?.workspace?.knowledge) {
				goto('/workspace/knowledge');
			// } else if ($user?.permissions?.workspace?.prompts) {
			// 	goto('/workspace/prompts');
			// } else if ($user?.permissions?.workspace?.tools) {
			// 	goto('/workspace/tools');
			} else {
				goto('/');
			}
		} else {
			goto('/workspace/agents');
		}
	});
</script>
