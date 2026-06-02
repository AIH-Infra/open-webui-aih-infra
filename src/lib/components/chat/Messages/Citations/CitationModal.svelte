<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { settings } from '$lib/stores';

	import XMark from '$lib/components/icons/XMark.svelte';
const i18n: any = getContext('i18n');

	const CONTENT_PREVIEW_LIMIT = 10000;
	let expandedDocs: Set<number> = new Set();

	export let show = false;
	export let citation;
	export let showPercentage = false;

	let mergedDocuments: any[] = [];

	function calculatePercentage(distance: number) {
		if (typeof distance !== 'number') return null;
		if (distance < 0) return 0;
		if (distance > 1) return 100;
		return Math.round(distance * 10000) / 100;
	}

	function getRelevanceColor(percentage: number) {
		if (percentage >= 80)
			return 'bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200';
		if (percentage >= 60)
			return 'bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200';
		if (percentage >= 40)
			return 'bg-orange-200 dark:bg-orange-800 text-orange-800 dark:text-orange-200';
		return 'bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200';
	}

	$: if (citation) {
		expandedDocs = new Set();
		mergedDocuments = citation.document?.map((c: any, i: number) => {
			return {
				source: citation.source,
				document: c,
				metadata: citation.metadata?.[i],
				distance: citation.distances?.[i]
			};
		});
		if (mergedDocuments.every((doc) => doc.distance !== undefined)) {
			mergedDocuments = mergedDocuments.sort(
				(a, b) => (b.distance ?? Infinity) - (a.distance ?? Infinity)
			);
		}
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch {
			return str;
		}
	};

	const formatPageRange = (start: number, end?: number) => {
		if (!start) return '';
		return end && end !== start ? `${start}-${end}` : `${start}`;
	};

	const getTextFragmentUrl = (doc: any): string | null => {
		const { metadata, source, document: content } = doc ?? {};
		const { file_id, page, page_start } = metadata ?? {};
		const sourceUrl = source?.url;

		const baseUrl = file_id
			? `${WEBUI_API_BASE_URL}/files/${file_id}/content${page_start !== undefined ? `#page=${page_start}` : page !== undefined ? `#page=${page + 1}` : ''}`
			: sourceUrl?.includes('http')
				? sourceUrl
				: null;

		if (!baseUrl || !content) return baseUrl;

		const words = content
			.trim()
			.replace(/\s+/g, ' ')
			.split(' ')
			.filter((w: string) => w.length > 0 && !/https?:\/\/|[\u{1F300}-\u{1F9FF}]/u.test(w));

		if (words.length === 0) return baseUrl;

		const clean = (w: string) => w.replace(/[^\w]/g, '');
		const first = clean(words[0]);
		const last = clean(words.at(-1));
		const fragment = words.length === 1 ? first : `${first},${last}`;

		return fragment ? `${baseUrl}#:~:text=${fragment}` : baseUrl;
	};
</script>

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-4.5 pt-3 pb-2">
			<div class=" text-lg font-medium self-center flex items-center">
				{#if citation?.source?.name}
					{@const document = mergedDocuments?.[0]}
					{#if document?.metadata?.file_id || document.source?.url?.includes('http')}
						<Tooltip
							className="w-fit"
							content={document.source?.url?.includes('http')
								? $i18n.t('Open link')
								: $i18n.t('Open file')}
							placement="top-start"
							tippyOptions={{ duration: [500, 0] }}
						>
							<a
								class="hover:text-gray-500 dark:hover:text-gray-100 underline grow line-clamp-1"
								href={document?.metadata?.file_id
									? `${WEBUI_API_BASE_URL}/files/${document?.metadata?.file_id}/content${document?.metadata?.page_start !== undefined ? `#page=${document.metadata.page_start}` : document?.metadata?.page !== undefined ? `#page=${document.metadata.page + 1}` : ''}`
									: document.source?.url?.includes('http')
										? document.source.url
										: `#`}
								target="_blank"
							>
								{decodeString(citation?.source?.name)}
							</a>
						</Tooltip>
					{:else}
						{decodeString(citation?.source?.name)}
					{/if}
				{:else}
					{$i18n.t('Citation')}
				{/if}
			</div>
			<button
				class="self-center"
				aria-label={$i18n.t('Close citation modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-5 md:space-x-4">
			<div
				class="flex flex-col w-full dark:text-gray-200 overflow-y-scroll max-h-[22rem] scrollbar-thin gap-0"
			>
				{#each mergedDocuments as document, documentIdx}
					{#if documentIdx > 0}
						<hr class="border-gray-100 dark:border-gray-800 my-2" />
					{/if}
					<div class="flex flex-col w-full gap-1.5 py-1">
						<!-- Row 1: chunk index + header breadcrumb -->
						<div class="flex items-baseline gap-2">
							<span class="text-[10px] font-semibold text-gray-400 dark:text-gray-500 shrink-0">#{documentIdx + 1}</span>
							{#if document?.metadata?.['Header 1'] || document?.metadata?.['Header 2']}
								<span class="text-xs font-medium text-gray-600 dark:text-gray-300 line-clamp-1">
									{#if document.metadata['Header 1']}{document.metadata['Header 1']}{/if}{#if document.metadata['Header 2']} › {document.metadata['Header 2']}{/if}
								</span>
							{/if}
						</div>

						<!-- Row 2: page info + relevance score -->
						<div class="flex items-center gap-3 flex-wrap">
							{#if document?.metadata?.page_start || document?.metadata?.print_page_start}
								{#if document?.metadata?.page_start}
									<span class="text-xs text-gray-500 dark:text-gray-400">p. {formatPageRange(document.metadata.page_start, document.metadata.page_end)}</span>
								{/if}
								{#if document?.metadata?.print_page_start}
									<span class="text-xs text-gray-500 dark:text-gray-400">printed p. {formatPageRange(document.metadata.print_page_start, document.metadata.print_page_end)}</span>
								{/if}
							{:else if Number.isInteger(document?.metadata?.page)}
								<span class="text-xs text-gray-500 dark:text-gray-400">p. {document.metadata.page + 1}</span>
							{/if}

							{#if typeof document?.distance === 'number'}
								{#if showPercentage}
									{@const percentage = calculatePercentage(document.distance)}
									{#if typeof percentage === 'number'}
										<span class={`text-xs px-1.5 py-0.5 rounded font-medium ${getRelevanceColor(percentage)}`}>{percentage.toFixed(1)}%</span>
									{/if}
								{:else}
									<span class="text-xs text-gray-400 dark:text-gray-500">score {document.distance.toFixed(4)}</span>
								{/if}
							{/if}

							{#if document.source?.url?.includes('http')}
								{@const snippetUrl = getTextFragmentUrl(document)}
								{#if snippetUrl}
									<a href={snippetUrl} target="_blank" class="text-xs text-blue-500 hover:underline ml-auto shrink-0">{$i18n.t('Open')}</a>
								{/if}
							{/if}
						</div>

						<!-- Row 3: content -->
						{#if document.metadata?.html}
							<iframe
								class="w-full border-0 h-auto rounded-none"
								sandbox="allow-scripts allow-forms{($settings?.iframeSandboxAllowSameOrigin ?? false)
									? ' allow-same-origin'
									: ''}"
								srcdoc={document.document}
								title={$i18n.t('Content')}
							></iframe>
						{:else}
							{@const rawContent = document.document.trim().replace(/\n\n+/g, '\n\n')}
							{@const isTruncated =
								($settings?.renderMarkdownInPreviews ?? true) &&
								rawContent.length > CONTENT_PREVIEW_LIMIT &&
								!expandedDocs.has(documentIdx)}
							{#if $settings?.renderMarkdownInPreviews ?? true}
								<div class="text-sm prose dark:prose-invert max-w-full">
									<Markdown
										content={isTruncated ? rawContent.slice(0, CONTENT_PREVIEW_LIMIT) : rawContent}
										id="citation-{documentIdx}"
									/>
								</div>
								{#if isTruncated}
									<button
										class="mt-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
										on:click={() => {
											expandedDocs.add(documentIdx);
											expandedDocs = expandedDocs;
										}}
									>
										{$i18n.t('Show all ({{COUNT}} characters)', {
											COUNT: rawContent.length.toLocaleString()
										})}
									</button>
								{/if}
							{:else}
								<pre class="text-sm dark:text-gray-400 whitespace-pre-line">{rawContent}</pre>
							{/if}
						{/if}
					</div>
				{/each}
			</div>
		</div>
	</div>
</Modal>
