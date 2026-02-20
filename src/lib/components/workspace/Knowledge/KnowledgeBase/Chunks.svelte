<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getKnowledgeChunks } from '$lib/apis/knowledge';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let knowledgeId: string;

	let loading = false;
	let chunks = [];
	let statistics = null;
	let currentPage = 1;
	let pageSize = 20;
	let selectedChunk = null;

	onMount(async () => {
		await loadChunks();
	});

	const loadChunks = async () => {
		loading = true;
		try {
			const offset = (currentPage - 1) * pageSize;
			const response = await getKnowledgeChunks(
				localStorage.token,
				knowledgeId,
				pageSize,
				offset
			);

			if (response) {
				chunks = response.chunks;
				statistics = response.statistics;
			}
		} catch (e) {
			console.error('Failed to load chunks:', e);
			toast.error($i18n.t('Failed to load chunks'));
		} finally {
			loading = false;
		}
	};

	const nextPage = () => {
		if (currentPage * pageSize < statistics?.total_count) {
			currentPage++;
			loadChunks();
		}
	};

	const prevPage = () => {
		if (currentPage > 1) {
			currentPage--;
			loadChunks();
		}
	};

	const formatNumber = (num: number) => {
		return num?.toLocaleString() || '0';
	};
</script>

<div class="flex flex-col h-full">
	{#if loading && !statistics}
		<div class="flex justify-center items-center h-64">
			<Spinner className="size-6" />
		</div>
	{:else if statistics}
		<!-- Statistics Section -->
		<div class="mb-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
			<h3 class="text-lg font-semibold mb-3">{$i18n.t('Chunk Statistics')}</h3>
			<div class="grid grid-cols-2 md:grid-cols-5 gap-4">
				<div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Total Chunks')}</div>
					<div class="text-2xl font-bold">{formatNumber(statistics.total_count)}</div>
				</div>
				<div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Total Tokens')}</div>
					<div class="text-2xl font-bold">{formatNumber(statistics.total_tokens)}</div>
				</div>
				<div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Avg Tokens')}</div>
					<div class="text-2xl font-bold">{Math.round(statistics.avg_tokens)}</div>
				</div>
				<div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Total Chars')}</div>
					<div class="text-2xl font-bold">{formatNumber(statistics.total_chars)}</div>
				</div>
				<div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Avg Chars')}</div>
					<div class="text-2xl font-bold">{Math.round(statistics.avg_chars)}</div>
				</div>
			</div>

			<!-- Token Distribution -->
			<div class="mt-4">
				<h4 class="text-sm font-semibold mb-2">{$i18n.t('Token Distribution')}</h4>
				<div class="grid grid-cols-5 gap-2">
					{#each Object.entries(statistics.token_distribution) as [range, count]}
						<div class="text-center p-2 bg-white dark:bg-gray-700 rounded">
							<div class="text-xs text-gray-500 dark:text-gray-400">{range}</div>
							<div class="text-lg font-semibold">{count}</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Character Distribution -->
			<div class="mt-4">
				<h4 class="text-sm font-semibold mb-2">{$i18n.t('Character Distribution')}</h4>
				<div class="grid grid-cols-5 gap-2">
					{#each Object.entries(statistics.char_distribution) as [range, count]}
						<div class="text-center p-2 bg-white dark:bg-gray-700 rounded">
							<div class="text-xs text-gray-500 dark:text-gray-400">{range}</div>
							<div class="text-lg font-semibold">{count}</div>
						</div>
					{/each}
				</div>
			</div>
		</div>

		<!-- Chunks List -->
		<div class="flex-1 overflow-y-auto">
			<div class="space-y-2">
				{#each chunks as chunk, idx}
					<div
						class="p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition"
						on:click={() => (selectedChunk = selectedChunk === chunk.id ? null : chunk.id)}
					>
						<div class="flex justify-between items-start mb-2">
							<div class="flex items-center gap-2">
								<span class="text-sm font-semibold text-gray-700 dark:text-gray-300">
									Chunk #{(currentPage - 1) * pageSize + idx + 1}
								</span>
								<span class="text-xs text-gray-500">
									{chunk.token_count} tokens | {chunk.char_count} chars
								</span>
							</div>
							<button
								class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
								on:click|stopPropagation={() =>
									(selectedChunk = selectedChunk === chunk.id ? null : chunk.id)}
							>
								{selectedChunk === chunk.id ? $i18n.t('Hide') : $i18n.t('Show')}
							</button>
						</div>

						{#if chunk.metadata?.source}
							<div class="text-xs text-gray-500 mb-2">
								{$i18n.t('Source')}: {chunk.metadata.source}
							</div>
						{/if}

						<div class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
							{chunk.content.substring(0, 200)}...
						</div>

						{#if selectedChunk === chunk.id}
							<div class="mt-3 p-3 bg-gray-100 dark:bg-gray-900 rounded text-sm whitespace-pre-wrap">
								{chunk.content}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>

		<!-- Pagination -->
		<div class="mt-4 flex justify-between items-center">
			<div class="text-sm text-gray-500">
				{$i18n.t('Showing')}
				{(currentPage - 1) * pageSize + 1}-{Math.min(
					currentPage * pageSize,
					statistics.total_count
				)}
				{$i18n.t('of')}
				{statistics.total_count}
			</div>
			<div class="flex gap-2">
				<button
					class="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={currentPage === 1}
					on:click={prevPage}
				>
					{$i18n.t('Previous')}
				</button>
				<button
					class="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={currentPage * pageSize >= statistics.total_count}
					on:click={nextPage}
				>
					{$i18n.t('Next')}
				</button>
			</div>
		</div>
	{:else}
		<div class="flex justify-center items-center h-64 text-gray-500">
			{$i18n.t('No chunks found')}
		</div>
	{/if}
</div>
