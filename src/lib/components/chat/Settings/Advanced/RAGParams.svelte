<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { getContext, onMount } from 'svelte';
	import { getRAGConfig } from '$lib/apis/retrieval';

	const i18n = getContext('i18n');

	export let onChange: (params: any) => void = () => {};
	export let admin = false;

	const defaultParams = {
		// RAG Parameters
		top_k: null, // Number of chunks to retrieve
		relevance_threshold: null, // Minimum relevance score
		chunk_size: null, // Chunk size for text splitting
		chunk_overlap: null, // Chunk overlap for text splitting
		global_top_k: true, // True: global top_k, False: per-source top_k
	};

	export let params = defaultParams;
	$: if (params) {
		onChange(params);
	}

	// Global defaults for display as placeholders
	let globalDefaults = {
		chunk_size: 1000,
		chunk_overlap: 100,
	};

	onMount(async () => {
		try {
			const config = await getRAGConfig(localStorage.token);
			if (config) {
				globalDefaults.chunk_size = config.CHUNK_SIZE || 1000;
				globalDefaults.chunk_overlap = config.CHUNK_OVERLAP || 100;
			}
		} catch (error) {
			console.error('Failed to fetch RAG config:', error);
		}
	});
</script>

<div class=" space-y-1 text-xs pb-safe-bottom">
	<!-- Top K -->
	<div>
		<Tooltip
			content={$i18n.t(
				'Number of relevant chunks to retrieve from knowledge bases. Higher values provide more context but may include less relevant information.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Top K')}
				</div>
				<div class="flex items-center">
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={$i18n.t('Default')}
						bind:value={params.top_k}
						min="1"
						max="512"
						on:input={() => {
							if (params.top_k === '') {
								params.top_k = null;
							}
						}}
					/>
				</div>
			</div>
		</Tooltip>
	</div>

	<!-- Relevance Threshold -->
	<div>
		<Tooltip
			content={$i18n.t(
				'Minimum similarity score (0-1) for retrieved chunks. Higher values return only more relevant results. This filters chunks based on their vector similarity to your query.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Relevance Threshold')}
				</div>
				<div class="flex items-center">
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={$i18n.t('Default')}
						bind:value={params.relevance_threshold}
						min="0"
						max="1"
						step="0.1"
						on:input={() => {
							if (params.relevance_threshold === '') {
								params.relevance_threshold = null;
							}
						}}
					/>
				</div>
			</div>
		</Tooltip>
	</div>

	<!-- Global Top K Toggle -->
	<div>
		<Tooltip
			content={$i18n.t(
				'When enabled (default), returns top K results across all knowledge bases and files combined. When disabled, each source returns K results separately.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Global Top K')}
				</div>
				<div class="flex items-center">
					<input
						type="checkbox"
						bind:checked={params.global_top_k}
						class="cursor-pointer"
					/>
				</div>
			</div>
		</Tooltip>
	</div>

	<!-- Chunk Size -->
	<div>
		<Tooltip
			content={$i18n.t(
				'Size of text chunks for splitting documents. Larger chunks provide more context but may reduce precision. Leave empty to use global default.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Chunk Size')}
				</div>
				<div class="flex items-center">
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={globalDefaults.chunk_size.toString()}
						bind:value={params.chunk_size}
						min="1"
						max="100000"
						on:input={() => {
							if (params.chunk_size === '') {
								params.chunk_size = null;
							}
						}}
					/>
				</div>
			</div>
		</Tooltip>
	</div>

	<!-- Chunk Overlap -->
	<div>
		<Tooltip
			content={$i18n.t(
				'Number of characters to overlap between chunks. Helps maintain context across chunk boundaries. Leave empty to use global default.'
			)}
			placement="top-start"
			className="inline-tooltip"
		>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Chunk Overlap')}
				</div>
				<div class="flex items-center">
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={globalDefaults.chunk_overlap.toString()}
						bind:value={params.chunk_overlap}
						min="0"
						max="10000"
						on:input={() => {
							if (params.chunk_overlap === '') {
								params.chunk_overlap = null;
							}
						}}
					/>
				</div>
			</div>
		</Tooltip>
	</div>
</div>

