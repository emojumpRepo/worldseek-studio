<script lang="ts">
	import { getContext } from 'svelte';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { WS_KB_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';

	dayjs.extend(relativeTime);
	const i18n = getContext('i18n');
	const nagivateToWorldSeekKB = () => {
		console.log('前往 WorldSeek KB 知识库');
		window.open(WS_KB_BASE_URL, '_blank');
	}


</script>

<!-- <svelte:head>
	<title>
		{$i18n.t('Knowledge')} | {$WEBUI_NAME}
	</title>
</svelte:head> -->
<div class="w-full h-full flex flex-col items-center justify-center gap-8">
	<img src="/static/worldseek_KB_logo.svg" alt="WorldSeek KB Logo" class="w-80 h-30" />
	<button class="bg-black text-white px-8 py-6 rounded-full text-2xl" on:click={nagivateToWorldSeekKB}>
		前往 WorldSeek KB 知识库
	</button>
</div>
