<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
    import { fade } from 'svelte/transition';
    import { Label, RadioGroup } from "bits-ui";

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

    export let agent = {
        name: '',
        description: '',
        params: {},
        access_control: {},
    }

	let modalElement = null;
	let mounted = false;
	let isClosing = false;

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			console.log('Escape');
			closeModal();
		}

		if (event.key === 'Enter') {
			console.log('Enter');
			confirmHandler();
		}
	};

	const closeModal = () => {
		if (isClosing) return;
		isClosing = true;
		setTimeout(() => {
			isClosing = false;
			show = false;
		}, 200); // 动画持续时间
	};

	const confirmHandler = async () => {
		closeModal();
		await onConfirm();
		dispatch('confirm', inputValue);
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

{#if show || isClosing}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={modalElement}
		class=" fixed top-0 right-0 left-0 bottom-0 bg-black/60 w-full h-screen max-h-[100dvh] flex justify-center z-99999999 overflow-hidden overscroll-contain"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			closeModal();
		}}
	>
		<div
			class="modal-content m-auto rounded-lg max-w-full w-[32rem] mx-2 bg-gray-50 dark:bg-gray-950 max-h-[100dvh] shadow-3xl {isClosing ? 'modal-closing' : ''}"
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<div class="p-3 flex flex-col">
                <!-- 设置弹窗头部（标题和关闭按钮） -->
				<div class="flex justify-between items-center mb-4">
                    <div class="font-medium dark:text-gray-200">
                        {$i18n.t('Model APP Settings')}
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
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="2"
                            stroke="currentColor"
                            class="w-5 h-5"
                        >
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

				<!-- 表单部分 -->
                <div class="flex flex-col gap-4">
                    <!-- 智能体名称 表单项 -->
                    <div class="flex flex-col gap-1">
                        <div class="flex justify-between items-center text-sm">
                            <div class="font-bold text-black">
                                {$i18n.t('Model Name')}
                            </div>
                            <div class="text-[#cccccc]">
                                通用智能体
                            </div>
                        </div>
                        <input type="text" class="w-full rounded-md border border-[#cccccc] py-1 px-2 text-sm" bind:value={agent.name} placeholder={$i18n.t('Model Name Placeholder')}/>
                    </div>

                    <!-- 智能体介绍 表单项 -->
                    <div class="flex flex-col gap-1">
                        <div class="font-bold text-black">
                            {$i18n.t('Model Description')}
                        </div>
                        <textarea class="w-full rounded-md border border-[#cccccc] py-1 px-2 text-sm" 
                            bind:value={agent.description} 
                            placeholder={$i18n.t('Model Description Placeholder')} 
                            rows={3}
                        />
                    </div>

                    <!-- 智能体访问权限 表单项 -->
                    <div class="flex justify-between items-center">
                        <div class="font-bold text-black">
                            {$i18n.t('Models Access')}
                        </div>
                        <RadioGroup.Root class="flex gap-6 text-sm font-bold">
                            <div
                              class="text-foreground group flex select-none items-center transition-all"
                            >
                              <RadioGroup.Item
                                id="private"
                                value="private"
                                class="border-border-input bg-background hover:border-dark-40 data-[state=checked]:border-6 data-[state=checked]:border-foreground size-5 shrink-0 cursor-default rounded-full border transition-all duration-100 ease-in-out"
                              />
                              <Label.Root for="private" class="pl-3">{$i18n.t('Models Access Private')}</Label.Root>
                            </div>
                            <div
                              class="text-foreground group flex select-none items-center transition-all"
                            >
                              <RadioGroup.Item
                                id="public"
                                value="public"
                                class="border-border-input bg-background hover:border-dark-40 data-[state=checked]:border-6 data-[state=checked]:border-foreground size-5 shrink-0 cursor-default rounded-full border transition-all duration-100 ease-in-out"
                              />
                              <Label.Root for="public" class="pl-3">{$i18n.t('Models Access Public')}</Label.Root>
                            </div>
                        </RadioGroup.Root>
                    </div>
                </div>

				<div class="mt-6 flex justify-between gap-1.5">
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-content {
		animation: scaleUp 0.2s ease-out forwards;
	}
    
    .modal-closing {
        animation: scaleDown 0.2s ease-out forwards;
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
