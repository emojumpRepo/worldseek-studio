<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { fade } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	
	export let value: string = '';
	export let options: Array<{ label: string; value: string }> = [];
	export let placeholder: string = '请选择';
	export let disabled: boolean = false;
	export let height: string = 'h-8';
	export let labelClass: string = 'text-sm';
    export let isShowIcon: boolean = true;
	
    let showDropdown: boolean = false;

	// 创建类型定义
	type FlyAndScaleParams = {
		y?: number;
		start?: number;
		duration?: number;
	};

	// 过渡效果
	function flyAndScale(node: HTMLElement, params: FlyAndScaleParams = {}) {
		const style = getComputedStyle(node);
		const transform = style.transform === 'none' ? '' : style.transform;
		const y = params.y ?? -8;
		const start = params.start ?? 0.95;
		const duration = params.duration ?? 200;
		
		return {
			duration,
			css: (t: number) => {
				const yValue = (1 - t) * y;
				const scale = start + (1 - start) * t;
				return `
					transform: ${transform} translate3d(0, ${yValue}px, 0) scale(${scale});
					opacity: ${t}
				`;
			},
			easing: cubicOut
		};
	}
	
	function toggleDropdown(): void {
		if (!disabled) {
			showDropdown = !showDropdown;
		}
	}
	
	function handleSelect(option: { label: string; value: string }): void {
		value = option.value;
		showDropdown = false;
	}
	
	// 显示标签的函数
	let selectedLabel = getSelectedLabel();
	
	function getSelectedLabel(): string {
		const selected = options.find(opt => opt.value === value);
		return selected ? selected.label : placeholder;
	}
	
	// 当值或选项改变时更新标签
	$: {
		value;
		options;
		selectedLabel = getSelectedLabel();
	}
	
	// 点击外部关闭下拉框
	let dropdownEl: HTMLElement;
	
	function handleClickOutside(event: MouseEvent): void {
		if (dropdownEl && !dropdownEl.contains(event.target as Node) && showDropdown) {
			showDropdown = false;
		}
	}
	
	onMount(() => {
		document.addEventListener('click', handleClickOutside);
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});
</script>

<div class="dropdown-container text-xs" bind:this={dropdownEl} role="combobox" aria-expanded={showDropdown}>
	<button 
		type="button"
		class="dropdown-trigger {height} {disabled ? 'opacity-60' : ''} {labelClass}"
		on:click={toggleDropdown}
		aria-expanded={showDropdown}
		aria-haspopup="listbox"
		disabled={disabled}
	>
		{selectedLabel}
		{#if isShowIcon}
			<svg
				class="dropdown-arrow"
				viewBox="0 0 20 20"
				fill="currentColor"
				aria-hidden="true"
			>
				<path
					fill-rule="evenodd"
					d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
					clip-rule="evenodd"
				/>
			</svg>
		{/if}
	</button>
	
	{#if showDropdown}
		<div 
			class="dropdown-menu"
			transition:flyAndScale
			role="listbox"
		>
			{#each options as option, i}
				<div 
					class="dropdown-item {option.value === value ? 'dropdown-item-selected' : ''}"
					on:click={() => handleSelect(option)}
					role="option"
					aria-selected={option.value === value}
					id={`option-${i}`}
					tabindex="0"
					on:keydown={(e) => e.key === 'Enter' && handleSelect(option)}
				>
					<div class="flex items-center justify-between">
						<span>{option.label}</span>
						{#if option.value === value}
							<svg
								class="dropdown-check"
								viewBox="0 0 20 20"
								fill="currentColor"
								aria-hidden="true"
							>
								<path
									fill-rule="evenodd"
									d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
									clip-rule="evenodd"
								/>
							</svg>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.dropdown-container {
		position: relative;
		width: 100%;
		border-radius: 0.375rem;
		border: 1px solid #d1d5db;
		background-color: white;
		cursor: pointer;
	}
	
	.dropdown-trigger {
		width: 100%;
		display: flex;
		justify-content: center;
		align-items: center;
		background-color: transparent;
		outline: none;
		cursor: pointer;
		border-radius: 0.375rem;
		border: none;
		text-align: center;
		padding: 0;
	}
	
	.dropdown-arrow {
		position: absolute;
		right: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		height: 1rem;
		width: 1rem;
		color: #6b7280;
		pointer-events: none;
	}
	
	.dropdown-menu {
		position: absolute;
		left: 0;
		right: 0;
		top: calc(100% + 4px);
		background-color: white;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
		z-index: 50;
		max-height: 15rem;
		overflow-y: auto;
	}
	
	.dropdown-item {
		padding: 0.5rem 0.75rem;
		cursor: pointer;
	}
	
	.dropdown-item:hover, .dropdown-item:focus {
		background-color: #f3f4f6;
		outline: none;
	}
	
	.dropdown-item-selected {
		background-color: #f3f4f6;
		color: #111827;
		font-weight: 500;
	}
	
	.dropdown-check {
		width: 1rem;
		height: 1rem;
		color: #111827;
	}
</style> 