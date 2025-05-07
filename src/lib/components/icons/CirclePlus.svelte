<script lang="ts">
	export let className = 'w-4 h-4';
	export let strokeWidth = '1.5';
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	fill="none"
	viewBox="0 0 24 24"
	stroke="currentColor"
	stroke-width={strokeWidth}
	class={className}
>
	<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5" fill="none" />
	<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v8m-4-4h8" />
</svg>
