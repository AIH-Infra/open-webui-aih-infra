<script lang="ts">
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { onMount, getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let ollamaVersion = '';

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch(() => {
			return '';
		});
	});
</script>

<div id="tab-about" class="flex flex-col h-full justify-between space-y-3 text-sm mb-6">
	<div class=" space-y-3 overflow-y-scroll max-h-[28rem] md:max-h-full">
		<div>
			<div class=" mb-2.5 text-sm font-medium flex space-x-2 items-center">
				<div>{$i18n.t('Version')}</div>
			</div>
			<div class="flex w-full">
				<div class="flex flex-col text-xs text-gray-700 dark:text-gray-200 space-y-1">
					<div class="font-medium text-sm text-gray-900 dark:text-white">AIH-Infra v1.0</div>
					<div>
						Based on Open WebUI
						<Tooltip content={WEBUI_BUILD_HASH}>
							v{WEBUI_VERSION}
						</Tooltip>
					</div>
					<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">Maintained by AIH-Infra.</div>
					<div class="text-xs text-gray-400 dark:text-gray-600">
						AIH-Infra customization contributions by Güriedrich &amp; Baireinhold.
					</div>
					<a class="underline text-gray-500 dark:text-gray-400" href="https://github.com/AIH-Infra/open-webui-aih-infra" target="_blank">
						AIH-Infra repository
					</a>
				</div>
			</div>
		</div>

		{#if ollamaVersion}
			<hr class=" border-gray-100/30 dark:border-gray-850/30" />

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Ollama Version')}</div>
				<div class="flex w-full">
					<div class="flex-1 text-xs text-gray-700 dark:text-gray-200">
						{ollamaVersion ?? 'N/A'}
					</div>
				</div>
			</div>
		{/if}

		<hr class=" border-gray-100/30 dark:border-gray-850/30" />

		<div class="space-y-2 text-xs">
			<div>
				<div class="mb-1 font-medium text-gray-700 dark:text-gray-200">Upstream project resources</div>
				<div class="flex flex-col gap-1">
					<a href="https://docs.openwebui.com/" target="_blank" class="underline text-gray-500 dark:text-gray-400">
						Open WebUI upstream documentation
					</a>
					<a href="https://github.com/open-webui/open-webui" target="_blank" class="underline text-gray-500 dark:text-gray-400">
						Open WebUI upstream repository
					</a>
				</div>
			</div>
		</div>
		<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
			Emoji graphics provided by
			<a href="https://github.com/jdecked/twemoji" target="_blank">Twemoji</a>, licensed under
			<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC-BY 4.0</a>.
		</div>

		<div class="mt-2 space-y-1 text-xs text-gray-400 dark:text-gray-500">
			<div class="font-medium">Upstream copyright notice</div>
			<div>
				Copyright (c) 2023- <a href="https://openwebui.com" target="_blank" class="underline">Open WebUI Inc.</a>. All rights reserved.
			</div>
			<div>
				Created by <a class="text-gray-500 dark:text-gray-300 font-medium" href="https://github.com/tjbck" target="_blank">Timothy Jaeryang Baek</a>.
			</div>
		</div>
	</div>
</div>
