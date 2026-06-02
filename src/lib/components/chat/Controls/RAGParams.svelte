<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { config } from '$lib/stores';
	import { createEventDispatcher, getContext } from 'svelte';

	const i18n: any = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let ragMode = null;
	export let agentRagConfig: any = {
		top_k: 8,
		agent_top_k: 8,
		k_reranker: 4,
		agent_result_budget: 64,
		scope: 'chat',
		allow_view_knowledge_file: false,
		allow_view_file: false,
		allow_view_note: false,
		allow_workspace_notes: false,
		allow_chat_history: false,
		enable_reranking: false
	};
	export let params: any = {
		hybrid: false,
		top_k: null,
		relevance_threshold: null,
		k_reranker: null,
		hybrid_bm25_weight: null,
		global_top_k: true,
		reranking_model: null,
		query_count: null,
		context_range: null
	};

	$: rerankingPresetModels = $config?.features?.rag_reranking_preset_models ?? [];
	$: rerankingEngine = $config?.features?.rag_reranking_engine;

	const notifyChange = () => {
		dispatch('change');
	};

	const clampNumber = (value: unknown, defaultValue: number, min: number, max: number) => {
		const parsedValue = Number(value);
		if (!Number.isFinite(parsedValue)) return defaultValue;
		return Math.min(Math.max(Math.trunc(parsedValue), min), max);
	};

	const updateAgentRagConfig = (values: Record<string, unknown>) => {
		agentRagConfig = {
			...(agentRagConfig ?? {}),
			...values
		};
		notifyChange();
	};

	const getInputValue = (event: Event) => (event.currentTarget as HTMLInputElement).value;

	$: if (agentRagConfig) {
		if (agentRagConfig.top_k === undefined || agentRagConfig.top_k === null || agentRagConfig.top_k === '') {
			agentRagConfig.top_k = 8;
		}
		if (
			agentRagConfig.agent_top_k === undefined ||
			agentRagConfig.agent_top_k === null ||
			agentRagConfig.agent_top_k === ''
		) {
			agentRagConfig.agent_top_k = agentRagConfig.top_k ?? 8;
		}
		if (agentRagConfig.k_reranker === undefined || agentRagConfig.k_reranker === null || agentRagConfig.k_reranker === '') {
			agentRagConfig.k_reranker = 4;
		}
		if (
			agentRagConfig.agent_result_budget === undefined ||
			agentRagConfig.agent_result_budget === null ||
			agentRagConfig.agent_result_budget === ''
		) {
			agentRagConfig.agent_result_budget = 64;
		}
		if (!agentRagConfig.scope) {
			agentRagConfig.scope = 'chat';
		}
		if (agentRagConfig.allow_view_knowledge_file === undefined) {
			agentRagConfig.allow_view_knowledge_file = false;
		}
		if (agentRagConfig.allow_view_file === undefined) {
			agentRagConfig.allow_view_file = false;
		}
		if (agentRagConfig.allow_view_note === undefined) {
			agentRagConfig.allow_view_note = false;
		}
		if (agentRagConfig.allow_workspace_notes === undefined) {
			agentRagConfig.allow_workspace_notes = false;
		}
		if (agentRagConfig.allow_chat_history === undefined) {
			agentRagConfig.allow_chat_history = false;
		}
		if (agentRagConfig.enable_reranking === undefined) {
			agentRagConfig.enable_reranking = false;
		}
		if (agentRagConfig.global_top_k === undefined) {
			agentRagConfig.global_top_k = true;
		}
		if (agentRagConfig.enable_reranking && agentRagConfig.k_reranker > agentRagConfig.top_k) {
			agentRagConfig.k_reranker = agentRagConfig.top_k;
		}
	}

	$: showRerankingModelSelector =
		rerankingEngine === 'external' &&
		rerankingPresetModels.length > 0 &&
		((ragMode !== 'agent' && params?.hybrid === true) ||
			(ragMode === 'agent' && agentRagConfig?.enable_reranking === true));

	$: if (params && params.reranking_model === '') {
		params.reranking_model = null;
	}

	$: if (params && params.hybrid === true && params.relevance_threshold === 0.7) {
		params.relevance_threshold = 0.3;
	} else if (params && params.hybrid === false && params.relevance_threshold === 0.3) {
		params.relevance_threshold = 0.7;
	}

	$: if (params && params.hybrid === true && !params.hybrid_bm25_weight) {
		params.hybrid_bm25_weight = 0.25;
	}

	$: if (params) {
		if (params.top_k === '') {
			params.top_k = null;
		}
		if (params.k_reranker === '') {
			params.k_reranker = null;
		}
		if (
			params.top_k !== null &&
			params.top_k !== undefined &&
			params.k_reranker !== null &&
			params.k_reranker !== undefined &&
			params.k_reranker > params.top_k
		) {
			params.k_reranker = params.top_k;
		}
	}
</script>

<div class="space-y-1 text-xs">
	{#if ragMode !== 'agent'}
		<div>
			<Tooltip
				content={$i18n.t('Enable hybrid search combining vector and BM25 keyword search.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Hybrid Search')}</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						type="button"
						on:click={() => {
							params.hybrid = params.hybrid === true ? false : true;
							notifyChange();
						}}
					>
						{#if params.hybrid === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</Tooltip>
		</div>

		<div>
			<Tooltip
				content={$i18n.t('Number of relevant chunks to retrieve from knowledge bases.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Top K')}</div>
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={$i18n.t('Default')}
						bind:value={params.top_k}
						min="1"
						max="512"
						on:input={() => {
							if (params.top_k === '') params.top_k = null;
							notifyChange();
						}}
					/>
				</div>
			</Tooltip>
		</div>
	{/if}

	{#if showRerankingModelSelector}
		<div>
			<Tooltip
				content={$i18n.t('Choose which admin-approved reranking model to use for this chat request.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between gap-2">
					<div class="self-center text-xs font-medium">{$i18n.t('Reranking Model')}</div>
					<select
						class="w-36 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						bind:value={params.reranking_model}
						on:change={notifyChange}
					>
						<option value="">{$i18n.t('Default')}</option>
						{#each rerankingPresetModels as model}
							<option value={model}>{model}</option>
						{/each}
					</select>
				</div>
			</Tooltip>
		</div>
	{/if}

	<div>
		<Tooltip
			content={$i18n.t('When enabled, returns top K results across all sources combined. When disabled, each source returns K results separately.')}
			placement="top-start"
		>
			<div class="py-0.5 flex w-full justify-between">
				<div class="self-center text-xs font-medium">{$i18n.t('Global Top K')}</div>
				<input
					type="checkbox"
					checked={ragMode === 'agent' ? agentRagConfig.global_top_k : params.global_top_k}
					on:change={(e) => {
						const checked = e.currentTarget?.checked ?? false;
						if (ragMode === 'agent') {
							agentRagConfig.global_top_k = checked;
							params.global_top_k = checked;
						} else {
							params.global_top_k = checked;
						}
						notifyChange();
					}}
					class="cursor-pointer"
				/>
			</div>
		</Tooltip>
	</div>

	{#if ragMode === 'agent'}
		<div>
			<Tooltip
				content={agentRagConfig.enable_reranking
					? $i18n.t('Number of candidate chunks to retrieve before Agent reranking.')
					: $i18n.t('Number of chunks to return for each Agent RAG query when reranking is off.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">
						{agentRagConfig.enable_reranking ? $i18n.t('Agent Candidate K') : $i18n.t('Agent Top K')}
					</div>
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder="8"
						value={agentRagConfig.enable_reranking ? agentRagConfig.top_k : agentRagConfig.agent_top_k}
						min="1"
						max="512"
						on:input={(event) => {
							const value = getInputValue(event);
							if (agentRagConfig.enable_reranking) {
								agentRagConfig.top_k = value === '' ? 8 : Number(value);
							} else {
								agentRagConfig.agent_top_k = value === '' ? 8 : Number(value);
							}
							if (agentRagConfig.enable_reranking && agentRagConfig.k_reranker > agentRagConfig.top_k) {
								agentRagConfig.k_reranker = agentRagConfig.top_k;
							}
							notifyChange();
						}}
					/>
				</div>
			</Tooltip>
		</div>

		<div>
			<Tooltip
				content={$i18n.t('Maximum retrieved chunks Agent RAG may feed back into one answer. Higher values allow deeper search but increase context size.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Agent Result Budget')}</div>
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder="64"
						value={agentRagConfig.agent_result_budget}
						min="32"
						max="256"
						step="32"
						on:input={(event) => {
							const value = getInputValue(event);
							updateAgentRagConfig({
								agent_result_budget: value === '' ? '' : Number(value)
							});
						}}
						on:change={() => {
							updateAgentRagConfig({
								agent_result_budget: clampNumber(
									agentRagConfig.agent_result_budget,
									64,
									32,
									256
								)
							});
						}}
					/>
				</div>
			</Tooltip>
		</div>

		<div>
			<Tooltip content={$i18n.t('Control whether Agent RAG stays within current chat knowledge or can search globally.')} placement="top-start">
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Scope')}</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						type="button"
						on:click={() => {
							agentRagConfig.scope = agentRagConfig.scope === 'chat' ? 'global' : 'chat';
							notifyChange();
						}}
					>
						<span class="ml-2 self-center">{agentRagConfig.scope === 'chat' ? $i18n.t('Chat') : $i18n.t('Global')}</span>
					</button>
				</div>
			</Tooltip>
		</div>

		<div>
			<Tooltip
				content={$i18n.t('Enable reranking for Agent RAG. When off, Agent retrieval keeps the current vector-only behavior even if a reranking model is selected.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Reranking')}</div>
					<input
						type="checkbox"
						bind:checked={agentRagConfig.enable_reranking}
						on:change={notifyChange}
						class="cursor-pointer"
					/>
				</div>
			</Tooltip>
		</div>

		{#if agentRagConfig.enable_reranking}
			<div>
				<Tooltip
					content={$i18n.t('Number of chunks to keep after Agent reranking. Must be less than or equal to Agent Candidate K.')}
					placement="top-start"
				>
					<div class="py-0.5 flex w-full justify-between">
						<div class="self-center text-xs font-medium">{$i18n.t('Agent Rerank K')}</div>
						<input
							class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
							type="number"
							placeholder="4"
							bind:value={agentRagConfig.k_reranker}
							min="1"
							max="512"
							on:input={() => {
								if (agentRagConfig.k_reranker === '') agentRagConfig.k_reranker = 4;
								if (agentRagConfig.k_reranker > agentRagConfig.top_k) {
									agentRagConfig.k_reranker = agentRagConfig.top_k;
								}
								notifyChange();
							}}
						/>
					</div>
				</Tooltip>
			</div>
		{/if}
	{/if}

	{#if ragMode !== 'agent' && params.hybrid === true}
		<div>
			<Tooltip
				content={$i18n.t('Minimum similarity score (0-1) for retrieved chunks.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Relevance Threshold')}</div>
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={$i18n.t('Default')}
						bind:value={params.relevance_threshold}
						min="0"
						max="1"
						step="0.1"
						on:input={() => {
							if (params.relevance_threshold === '') params.relevance_threshold = null;
							notifyChange();
						}}
					/>
				</div>
			</Tooltip>
		</div>

		<div>
			<Tooltip
				content={$i18n.t('BM25 keyword weight in hybrid search. 0 = pure vector, 0.5 = balanced, 1 = pure BM25.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('BM25 Weight')}</div>
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={$i18n.t('Default')}
						bind:value={params.hybrid_bm25_weight}
						min="0"
						max="1"
						step="0.05"
						on:input={() => {
							if (params.hybrid_bm25_weight === '') params.hybrid_bm25_weight = null;
							notifyChange();
						}}
					/>
				</div>
			</Tooltip>
		</div>

		<div>
			<Tooltip
				content={$i18n.t('Number of chunks to keep after reranking. Only effective when reranking is enabled.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Top K Reranker')}</div>
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={$i18n.t('Default')}
						bind:value={params.k_reranker}
						min="1"
						max={params.top_k ?? 512}
						on:input={() => {
							if (params.k_reranker === '') params.k_reranker = null;
							if (
								params.top_k !== null &&
								params.top_k !== undefined &&
								params.k_reranker !== null &&
								params.k_reranker !== undefined &&
								params.k_reranker > params.top_k
							) {
								params.k_reranker = params.top_k;
							}
							notifyChange();
						}}
					/>
				</div>
			</Tooltip>
		</div>
	{/if}

	{#if ragMode !== 'agent'}
		<div>
			<Tooltip
				content={$i18n.t('Number of search queries to generate (1-10). More queries provide broader coverage.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Query Count')}</div>
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={$i18n.t('Default')}
						bind:value={params.query_count}
						min="1"
						max="10"
						on:input={() => {
							if (params.query_count === '') params.query_count = null;
							notifyChange();
						}}
					/>
				</div>
			</Tooltip>
		</div>

		<div>
			<Tooltip
				content={$i18n.t('Number of recent messages to use as context (1-10) for query generation.')}
				placement="top-start"
			>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Context Range')}</div>
					<input
						class="w-16 rounded-lg py-1 px-2 text-xs bg-transparent text-right outline-hidden border border-gray-100 dark:border-gray-800"
						type="number"
						placeholder={$i18n.t('Default')}
						bind:value={params.context_range}
						min="1"
						max="10"
						on:input={() => {
							if (params.context_range === '') params.context_range = null;
							notifyChange();
						}}
					/>
				</div>
			</Tooltip>
		</div>
	{/if}
</div>
