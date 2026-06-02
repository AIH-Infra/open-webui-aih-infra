<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n: any = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import RAGParams from '$lib/components/chat/Controls/RAGParams.svelte';
	import ToolParams from '$lib/components/chat/Controls/ToolParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import { user, settings } from '$lib/stores';
	export let chatFiles: any[] = [];
	export let params: any = {};
	export let embed = false;
	export let collectionRefreshStates: Record<string, any> = {};
	export let refreshAttachedCollection: Function = () => {};

	const normalizeHybridValue = (value: unknown): boolean | undefined => {
		if (typeof value === 'boolean') return value;
		if (typeof value === 'string') {
			const normalized = value.trim().toLowerCase();
			if (['true', '1', 'yes', 'on'].includes(normalized)) return true;
			if (['false', '0', 'no', 'off'].includes(normalized)) return false;
		}
		return undefined;
	};

	// 确保 params 结构正确
	$: if (params) {
		if (!params.rag_mode) params.rag_mode = null;
		if (!params.agent_rag_config) {
			params.agent_rag_config = {
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
		}
		if (params.agent_rag_config.top_k === undefined || params.agent_rag_config.top_k === null || params.agent_rag_config.top_k === '') {
			params.agent_rag_config.top_k = 8;
		}
		if (
			params.agent_rag_config.agent_top_k === undefined ||
			params.agent_rag_config.agent_top_k === null ||
			params.agent_rag_config.agent_top_k === ''
		) {
			params.agent_rag_config.agent_top_k = params.agent_rag_config.top_k ?? 8;
		}
		if (params.agent_rag_config.k_reranker === undefined || params.agent_rag_config.k_reranker === null || params.agent_rag_config.k_reranker === '') {
			params.agent_rag_config.k_reranker = 4;
		}
		if (params.agent_rag_config.agent_result_budget === undefined || params.agent_rag_config.agent_result_budget === null || params.agent_rag_config.agent_result_budget === '') {
			params.agent_rag_config.agent_result_budget = 64;
		}
		if (!params.agent_rag_config.scope) {
			params.agent_rag_config.scope = 'chat';
		}
		if (params.agent_rag_config.allow_view_knowledge_file === undefined) {
			params.agent_rag_config.allow_view_knowledge_file = false;
		}
		if (params.agent_rag_config.allow_view_file === undefined) {
			params.agent_rag_config.allow_view_file = false;
		}
		if (params.agent_rag_config.allow_view_note === undefined) {
			params.agent_rag_config.allow_view_note = false;
		}
		if (params.agent_rag_config.allow_workspace_notes === undefined) {
			params.agent_rag_config.allow_workspace_notes = false;
		}
		if (params.agent_rag_config.allow_chat_history === undefined) {
			params.agent_rag_config.allow_chat_history = false;
		}
		if (params.agent_rag_config.enable_reranking === undefined) {
			params.agent_rag_config.enable_reranking = false;
		}
		if (params.agent_rag_config.global_top_k === undefined) {
			params.agent_rag_config.global_top_k = true;
		}
		if (
			params.agent_rag_config.enable_reranking &&
			params.agent_rag_config.k_reranker > params.agent_rag_config.top_k
		) {
			params.agent_rag_config.k_reranker = params.agent_rag_config.top_k;
		}
		if (!params.rag) {
			params.rag = {
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
		}
		if (params.rag.global_top_k === undefined) {
			params.rag.global_top_k = true;
		}
		if (params.rag_mode === 'agent') {
			params.rag.global_top_k = params.agent_rag_config.global_top_k;
		}
		const normalizedHybrid = normalizeHybridValue(params.rag.hybrid);
		params.rag.hybrid = normalizedHybrid ?? false;
		if (params.rag.reranking_model === undefined) params.rag.reranking_model = null;
	}

	// Persist collapsible section open/close state
	const getOpen = (key: string, fallback = true): boolean => {
		const v = localStorage.getItem(`chatControls.${key}`);
		return v !== null ? v === 'true' : fallback;
	};
	const setOpen = (key: string) => (open: boolean) => {
		localStorage.setItem(`chatControls.${key}`, String(open));
	};

	let showFiles = getOpen('files');
	let showValves = getOpen('valves', false);
	let showSystemPrompt = getOpen('systemPrompt');
	let showAdvancedParams = getOpen('advancedParams');
	let showRagParams = getOpen('ragParams', false);
	let showToolParams = getOpen('toolParams', false);

	// Collection expand state
	let expandedCollections: Record<number, boolean> = {};

	const toggleCollection = (idx: number) => {
		expandedCollections = {
			...expandedCollections,
			[idx]: !expandedCollections[idx]
		};
	};

	const notifyChange = () => {
		dispatch('change');
	};

	const toggleAllFiles = (fileIdx: number, enabled: boolean) => {
		chatFiles[fileIdx].files.forEach((f: any) => (f.enabled = enabled));
		chatFiles[fileIdx].allFilesEnabled = enabled;
		chatFiles = chatFiles;
		notifyChange();
	};
</script>

<div class=" dark:text-white">
	{#if !embed}
		<div class=" flex items-center justify-between dark:text-gray-100 mb-2">
			<div class=" text-md self-center font-primary">{$i18n.t('Controls')}</div>
			<button
				class="self-center"
				aria-label={$i18n.t('Close chat controls')}
				on:click={() => {
					dispatch('close');
				}}
			>
				<XMark className="size-3.5" />
			</button>
		</div>
	{/if}

	{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
		<div class=" dark:text-gray-200 text-sm py-0.5 px-0.5">
			{#if chatFiles.length > 0}
				<Collapsible
					title={$i18n.t('Files')}
					bind:open={showFiles}
					onChange={setOpen('files')}
					buttonClassName="w-full"
				>
					<div class="flex flex-col gap-1 mt-1.5" slot="content">
						{#each chatFiles as file, fileIdx}
							{#if file.type === 'collection' && file.files}
								<!-- Collection with expandable file list -->
								<div class="w-full border border-gray-200 dark:border-gray-700 rounded-lg">
									<div class="flex items-center gap-2 p-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" on:click={() => toggleCollection(fileIdx)}>
										<div class="shrink-0">
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
												<path d="M3 3.5A1.5 1.5 0 014.5 2h6.879a1.5 1.5 0 011.06.44l4.122 4.12A1.5 1.5 0 0117 7.622V16.5a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 013 16.5v-13z" />
											</svg>
										</div>
										<span class="flex-1 text-sm font-medium truncate">{file.name}</span>
										<button class="text-xs px-2 py-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700" on:click|stopPropagation={() => toggleAllFiles(fileIdx, !file.allFilesEnabled)}>
											{file.allFilesEnabled ? $i18n.t('Deselect All') : $i18n.t('Select All')}
										</button>
										<button class="shrink-0 p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded" on:click|stopPropagation={() => { chatFiles.splice(fileIdx, 1); chatFiles = chatFiles; notifyChange(); }}>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
												<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
											</svg>
										</button>
									</div>
									{#if collectionRefreshStates[file.id]}
										<div class="px-2 pb-2 text-[11px] text-gray-500 dark:text-gray-400 flex items-center justify-between gap-2">
											<div>
												{#if collectionRefreshStates[file.id].status === 'checking'}
													{$i18n.t('Checking for knowledge updates...')}
												{:else if collectionRefreshStates[file.id].status === 'stale'}
													{$i18n.t('Knowledge updated: {{added}} added, {{removed}} removed.', {
														added: collectionRefreshStates[file.id].addedCount ?? 0,
														removed: collectionRefreshStates[file.id].removedCount ?? 0
													})}
												{:else if collectionRefreshStates[file.id].status === 'refreshing'}
													{$i18n.t('Refreshing knowledge snapshot...')}
												{:else if collectionRefreshStates[file.id].status === 'unavailable'}
													{$i18n.t('Knowledge source is unavailable.')}
												{:else if collectionRefreshStates[file.id].status === 'error'}
													{$i18n.t('Failed to check knowledge updates.')}
												{/if}
											</div>
											{#if ['stale', 'error'].includes(collectionRefreshStates[file.id].status)}
												<button
													class="shrink-0 px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
													on:click|stopPropagation={() => refreshAttachedCollection(String(file.id))}
												>
													{$i18n.t('Refresh')}
												</button>
											{/if}
										</div>
									{/if}
									{#if expandedCollections[fileIdx]}
										<div class="border-t border-gray-200 dark:border-gray-700 px-2 py-2">
											<!-- Boost control -->
											<div class="mb-2 pb-2 border-b border-gray-200 dark:border-gray-700">
												<div class="flex items-center justify-between mb-1">
													<span class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Weight Boost')}</span>
													<span class="text-xs font-mono font-medium">{file.boost?.toFixed(1) || '1.0'}×</span>
												</div>
												<input
													type="range"
													min="0.1"
													max="2.0"
													step="0.1"
													bind:value={file.boost}
													on:input={() => { chatFiles = chatFiles; notifyChange(); }}
													class="w-full h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
												/>
											</div>
											<!-- File list -->
											<div class="max-h-48 overflow-y-auto">
												{#each file.files as subFile}
													<label class="flex items-center gap-2 p-1.5 hover:bg-gray-50 dark:hover:bg-gray-800 rounded cursor-pointer">
														<input type="checkbox" bind:checked={subFile.enabled} class="cursor-pointer" on:change={() => { file.allFilesEnabled = file.files.every((f: any) => f.enabled); chatFiles = chatFiles; notifyChange(); }} />
														<span class="text-xs truncate flex-1">{subFile.filename}</span>
													</label>
												{/each}
											</div>
										</div>
									{/if}
								</div>
							{:else}
								<!-- Regular file -->
								<FileItem
									className="w-full"
									item={file}
									edit={true}
									url={file?.url ? file.url : null}
									name={file.name}
									type={file.type}
									size={file?.size}
									dismissible={true}
									small={true}
									on:dismiss={() => {
										chatFiles.splice(fileIdx, 1);
										chatFiles = chatFiles;
										notifyChange();
									}}
									on:click={() => {
										console.log(file);
									}}
								/>
							{/if}
						{/each}
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.valves ?? true)}
				<Collapsible
					bind:open={showValves}
					onChange={setOpen('valves')}
					title={$i18n.t('Valves')}
					buttonClassName="w-full"
				>
					<div class="text-sm" slot="content">
						<Valves show={showValves} />
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
				<Collapsible
					title={$i18n.t('System Prompt')}
					bind:open={showSystemPrompt}
					onChange={setOpen('systemPrompt')}
					buttonClassName="w-full"
				>
					<div class="" slot="content">
						<textarea
							bind:value={params.system}
								on:input={notifyChange}
							class="w-full text-xs outline-hidden resize-vertical {$settings.highContrastMode
								? 'border-2 border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5'
								: 'py-1.5 bg-transparent'}"
							rows="4"
							placeholder={$i18n.t('Enter system prompt')}
						/>
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.params ?? true)}
				<Collapsible
					title={$i18n.t('LLM Params')}
					bind:open={showAdvancedParams}
					onChange={setOpen('advancedParams')}
					buttonClassName="w-full"
				>
					<div class="text-sm mt-1.5" slot="content">
						<div>
							<AdvancedParams admin={$user?.role === 'admin'} custom={true} bind:params onChange={notifyChange} />
						</div>
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />

				<!-- RAG Mode Selector -->
				<div class="space-y-1 text-xs">
					<div class="py-0.5 flex w-full justify-between">
						<div class="self-center text-xs font-medium">{$i18n.t('RAG Mode')}</div>
						<button
							class="p-1 px-3 text-xs flex rounded-sm transition"
							type="button"
							on:click={() => {
								const modes = [null, 'agent', 'disabled'];
								const idx = modes.indexOf(params.rag_mode);
								params.rag_mode = modes[(idx + 1) % 3];
									notifyChange();
							}}
						>
							{#if params.rag_mode === null}
								<span class="ml-2">{$i18n.t('Traditional')}</span>
							{:else if params.rag_mode === 'agent'}
								<span class="ml-2">{$i18n.t('Agent')}</span>
							{:else}
								<span class="ml-2">{$i18n.t('Disabled')}</span>
							{/if}
						</button>
					</div>

				</div>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />

				{#if params.rag_mode !== 'disabled'}
					<Collapsible
						title={$i18n.t('RAG Params')}
						bind:open={showRagParams}
						onChange={setOpen('ragParams')}
						buttonClassName="w-full"
					>
						<div class="text-sm mt-1.5" slot="content">
							<RAGParams
								bind:params={params.rag}
								bind:agentRagConfig={params.agent_rag_config}
								ragMode={params.rag_mode}
								on:change={notifyChange}
							/>
						</div>
					</Collapsible>

					<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
				{/if}

				<Collapsible
					title={$i18n.t('Tool Params')}
					bind:open={showToolParams}
					onChange={setOpen('toolParams')}
					buttonClassName="w-full"
				>
					<div class="text-sm mt-1.5" slot="content">
						<ToolParams bind:agentRagConfig={params.agent_rag_config} ragMode={params.rag_mode} on:change={notifyChange} />
					</div>
				</Collapsible>
			{/if}
		</div>
	{/if}
</div>
