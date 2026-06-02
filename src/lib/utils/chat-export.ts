const DATE_FORMATTER = new Intl.DateTimeFormat('sv-SE', {
	year: 'numeric',
	month: '2-digit',
	day: '2-digit'
});

const isObject = (value: unknown): value is Record<string, any> =>
	typeof value === 'object' && value !== null && !Array.isArray(value);

const toSafeArray = <T>(value: T[] | undefined | null): T[] => (Array.isArray(value) ? value : []);

const slugify = (value: string | null | undefined) =>
	(value ?? 'model')
		.replace(/[\\/:*?"<>|]+/g, '-')
		.replace(/\s+/g, '-')
		.replace(/-+/g, '-')
		.replace(/^-|-$/g, '') || 'model';

const getExportDate = () => DATE_FORMATTER.format(new Date());

const getExportedAt = () => new Date().toISOString();

const stringifyPretty = (value: unknown) => JSON.stringify(value, null, 2);

const extractStatusByAction = (statusHistory: any[], action: string) =>
	toSafeArray(statusHistory).find((status) => status?.action === action);

const collectToolCalls = (messageOutput: any[]) => {
	const callsById = new Map<string, any>();
	const transcript: any[] = [];

	for (const item of toSafeArray(messageOutput)) {
		if (item?.type === 'function_call') {
			const record = {
				index: transcript.length,
				tool_name: item?.name ?? '',
				arguments: (() => {
					try {
						return item?.arguments ? JSON.parse(item.arguments) : {};
					} catch {
						return item?.arguments ?? {};
					}
				})(),
				raw_arguments: item?.arguments ?? '',
				call_id: item?.call_id ?? '',
				output: null,
				files: [],
				embeds: []
			};
			transcript.push(record);
			if (record.call_id) {
				callsById.set(record.call_id, record);
			}
		}

		if (item?.type === 'function_call_output') {
			const target = callsById.get(item?.call_id ?? '');
			if (!target) {
				continue;
			}

			target.output = toSafeArray(item?.output)
				.map((outputItem) => outputItem?.text ?? '')
				.join('\n')
				.trim();
			target.files = toSafeArray(item?.files);
			target.embeds = toSafeArray(item?.embeds);
		}
	}

	return transcript;
};

const collectAgentQueries = (messageOutput: any[]) => {
	return collectToolCalls(messageOutput)
		.filter((call) => call.tool_name === 'query_knowledge_files')
		.map((call) => call.arguments?.query)
		.filter(Boolean);
};

const extractTraditionalQueries = (statusHistory: any[]) => {
	const knowledgeSearch = extractStatusByAction(statusHistory, 'knowledge_search');
	const generated = extractStatusByAction(statusHistory, 'queries_generated');

	return {
		knowledge_search_query: knowledgeSearch?.query ?? null,
		generated_queries: toSafeArray(generated?.queries)
	};
};

const toChunkRecord = (source: any, index: number) => {
	const metadata = toSafeArray(source?.metadata)[index] ?? {};
	const text = toSafeArray(source?.document)[index] ?? '';
	const distance = toSafeArray(source?.distances)[index] ?? null;
	const chunkKind = metadata?.content ? 'full_document' : 'chunk';

	return {
		index,
		text,
		score: distance,
		distance,
		char_count: typeof text === 'string' ? text.length : null,
		token_count: metadata?.token_count ?? null,
		page_start: metadata?.page_start ?? null,
		page_end: metadata?.page_end ?? null,
		print_page_start: metadata?.print_page_start ?? null,
		print_page_end: metadata?.print_page_end ?? null,
		file_id: metadata?.file_id ?? null,
		note_id: metadata?.note_id ?? null,
		knowledge_id: metadata?.knowledge_id ?? null,
		title: metadata?.title ?? null,
		metadata,
		chunk_kind: chunkKind
	};
};

const buildSourceRecords = (sources: any[]) =>
	toSafeArray(sources).map((source) => ({
		source_id: source?.source?.id ?? null,
		source_name: source?.source?.name ?? null,
		source_type: source?.source?.type ?? null,
		source_info: source?.source ?? {},
		chunks: toSafeArray(source?.document).map((_: unknown, index: number) =>
			toChunkRecord(source, index)
		)
	}));

const buildNormalizedRagParams = (ragSnapshot: any) => {
	const rag = isObject(ragSnapshot?.rag) ? ragSnapshot.rag : {};
	const agent = isObject(ragSnapshot?.agent_rag_config) ? ragSnapshot.agent_rag_config : {};

	return {
		rag_mode: ragSnapshot?.rag_mode ?? 'traditional',
		hybrid: rag?.hybrid ?? null,
		top_k: rag?.top_k ?? agent?.top_k ?? null,
		k_reranker: rag?.k_reranker ?? agent?.k_reranker ?? null,
		agent_result_budget: agent?.agent_result_budget ?? null,
		global_top_k: rag?.global_top_k ?? agent?.global_top_k ?? null,
		relevance_threshold: rag?.relevance_threshold ?? null,
		hybrid_bm25_weight: rag?.hybrid_bm25_weight ?? null,
		query_count: rag?.query_count ?? null,
		context_range: rag?.context_range ?? null,
		scope: agent?.scope ?? null,
		allow_view_knowledge_file: agent?.allow_view_knowledge_file ?? null,
		allow_view_file: agent?.allow_view_file ?? null,
		allow_view_note: agent?.allow_view_note ?? null,
		allow_workspace_notes: agent?.allow_workspace_notes ?? null,
		allow_chat_history: agent?.allow_chat_history ?? null,
		enable_reranking: agent?.enable_reranking ?? null,
		reranking_model: ragSnapshot?.reranking_model ?? null
	};
};

const buildResultSemantics = (ragSnapshot: any, statusHistory: any[]) => {
	const rag = isObject(ragSnapshot?.rag) ? ragSnapshot.rag : {};
	const agent = isObject(ragSnapshot?.agent_rag_config) ? ragSnapshot.agent_rag_config : {};
	const mode = ragSnapshot?.rag_mode ?? 'traditional';
	const rerankApplied =
		mode === 'agent'
			? (agent?.enable_reranking ?? null)
			: Boolean(rag?.hybrid) && (rag?.k_reranker ?? null) !== null;

	return {
		result_stage: 'final',
		rerank_applied: rerankApplied,
		analytics_confidence: mode === 'agent' ? 'partial' : 'high',
		status_event_count: toSafeArray(statusHistory).length
	};
};

const collectDistances = (sourceRecords: any[]): number[] =>
	toSafeArray(sourceRecords).flatMap((s) => toSafeArray(s?.chunks).map((c: any) => c?.distance).filter((d: any) => typeof d === 'number'));

const buildSummary = (sourceRecords: any[], statusHistory: any[]) => {
	const distances = collectDistances(sourceRecords);
	const sourcesRetrieved = extractStatusByAction(statusHistory, 'sources_retrieved');
	const chunkCount = sourceRecords.reduce((count, source) => count + toSafeArray(source?.chunks).length, 0);

	return {
		source_count: sourceRecords.length,
		chunk_count: chunkCount,
		score_min: distances.length ? Math.min(...distances) : null,
		score_max: distances.length ? Math.max(...distances) : null,
		score_avg: distances.length
			? distances.reduce((sum, distance) => sum + distance, 0) / distances.length
			: null,
		rag_doc_count: sourcesRetrieved?.rag_doc_count ?? null,
		rag_token_count: sourcesRetrieved?.rag_token_count ?? null
	};
};

export const formatRagSummary = (ragSnapshot: any) => {
	if (!isObject(ragSnapshot)) {
		return null;
	}

	const ragMode = ragSnapshot?.rag_mode ?? 'traditional';
	const rag = isObject(ragSnapshot?.rag) ? ragSnapshot.rag : {};
	const agent = isObject(ragSnapshot?.agent_rag_config) ? ragSnapshot.agent_rag_config : {};
	const tokens: string[] = [];

	switch (ragMode) {
		case 'agent':
			tokens.push('Agent');
			tokens.push(agent?.scope === 'global' ? 'Global' : 'Chat');
			if (agent?.enable_reranking) tokens.push('Rerank');
			if (agent?.allow_view_knowledge_file) tokens.push('KB file read');
			if (agent?.allow_view_file) tokens.push('WebUI files');
			if (agent?.allow_view_note) tokens.push('WebUI notes');
			if (agent?.allow_workspace_notes) tokens.push('Workspace notes');
			if (agent?.allow_chat_history) tokens.push('Chat history');
			break;
		case 'disabled':
			tokens.push('Disabled');
			if (agent?.allow_view_knowledge_file) tokens.push('KB file read');
			if (agent?.allow_view_file) tokens.push('WebUI files');
			if (agent?.allow_view_note) tokens.push('WebUI notes');
			if (agent?.allow_workspace_notes) tokens.push('Workspace notes');
			if (agent?.allow_chat_history) tokens.push('Chat history');
			break;
		default:
			tokens.push('Traditional');
			if (rag?.hybrid) tokens.push('Hybrid');
			if (rag?.hybrid && (rag?.k_reranker ?? null) !== null) tokens.push('Rerank');
			if (agent?.allow_view_knowledge_file) tokens.push('KB file read');
			if (agent?.allow_view_file) tokens.push('WebUI files');
			if (agent?.allow_view_note) tokens.push('WebUI notes');
			if (agent?.allow_workspace_notes) tokens.push('Workspace notes');
			if (agent?.allow_chat_history) tokens.push('Chat history');
			break;
	}

	return `[RAG: ${tokens.join('；')}]`;
};

export const buildEvidenceExport = ({ chatId, message, questionMessage }: any) => {
	const statusHistory = toSafeArray(message?.statusHistory);
	const sourceRecords = buildSourceRecords(message?.sources);
	const ragSnapshot = message?.ragSnapshot ?? {};
	const ragMode = ragSnapshot?.rag_mode ?? 'traditional';
	const traditionalQueries = extractTraditionalQueries(statusHistory);
	const agentQueries = collectAgentQueries(message?.output);
	const ragParams = buildNormalizedRagParams(ragSnapshot);
	const resultSemantics = buildResultSemantics(ragSnapshot, statusHistory);

	return {
		export_version: 'answer-evidence-v1',
		export_scope: 'evidence',
		format: 'json',
		exported_at: getExportedAt(),
		chat_id: chatId,
		message_id: message?.id ?? null,
		message_timestamp: message?.timestamp ?? null,
		model_id: message?.model ?? null,
		model_name: message?.modelName ?? null,
		retrieval_models: {
			embedding_model: ragSnapshot?.embedding_model ?? null,
			reranking_model: ragSnapshot?.reranking_model ?? null
		},
		question: questionMessage?.content ?? null,
		queries: {
			knowledge_search_query: traditionalQueries.knowledge_search_query,
			generated_queries: traditionalQueries.generated_queries,
			tool_queries: agentQueries
		},
		rag_snapshot: ragSnapshot,
		rag_params: ragParams,
		usage: message?.usage ?? null,
		summary: {
			...buildSummary(sourceRecords, statusHistory),
			...resultSemantics
		},
		sources: sourceRecords,
		evidence_mode: ragMode === 'agent' ? 'agent' : ragMode === 'disabled' ? 'none' : 'traditional'
	};
};

export const buildTraceExport = ({ chatId, message, questionMessage }: any) => {
	const sourceRecords = buildSourceRecords(message?.sources);
	const statusHistory = toSafeArray(message?.statusHistory);
	const toolTranscript = collectToolCalls(message?.output);
	const evidenceBundle = buildEvidenceExport({ chatId, message, questionMessage });

	return {
		export_version: 'answer-trace-v1',
		export_scope: 'trace',
		format: 'json',
		exported_at: getExportedAt(),
		chat_id: chatId,
		message_id: message?.id ?? null,
		message_timestamp: message?.timestamp ?? null,
		model: {
			id: message?.model ?? null,
			name: message?.modelName ?? null
		},
		rag_snapshot: message?.ragSnapshot ?? {},
		rag_params: evidenceBundle.rag_params,
		question: {
			message_id: questionMessage?.id ?? null,
			content: questionMessage?.content ?? null
		},
		answer: {
			message_id: message?.id ?? null,
			content: message?.content ?? null
		},
		usage: message?.usage ?? null,
		summary: {
			...evidenceBundle.summary,
			status_count: statusHistory.length,
			tool_call_count: toolTranscript.length
		},
		queries: evidenceBundle.queries,
		sources: sourceRecords,
		status_history: statusHistory,
		message_output: toSafeArray(message?.output),
		tool_transcript: toolTranscript,
		notes: ['Observable trace only; does not include hidden internal reasoning.']
	};
};

const renderSourceMarkdown = (source: any) => {
	const header = `## ${source.source_name ?? 'Unknown Source'}`;
	const meta = [
		`- Source ID: ${source.source_id ?? 'N/A'}`,
		`- Source Type: ${source.source_type ?? 'N/A'}`,
		`- Chunk Count: ${toSafeArray(source.chunks).length}`
	].join('\n');
	const chunks = toSafeArray(source.chunks)
		.map((chunk: any) => {
			const lines = [`### Chunk ${chunk.index + 1}`];
			if (chunk.score != null) lines.push(`- Score: ${chunk.score}`);
			if (chunk.file_id != null) lines.push(`- File ID: ${chunk.file_id}`);
			if (chunk.note_id != null) lines.push(`- Note ID: ${chunk.note_id}`);
			if (chunk.knowledge_id != null) lines.push(`- Knowledge ID: ${chunk.knowledge_id}`);
			if (chunk.page_start != null || chunk.page_end != null) lines.push(`- Pages: ${chunk.page_start ?? '?'}-${chunk.page_end ?? '?'}`);
			if (chunk.print_page_start != null || chunk.print_page_end != null) lines.push(`- Printed Pages: ${chunk.print_page_start ?? '?'}-${chunk.print_page_end ?? '?'}`);
			if (chunk.text) lines.push('', chunk.text);
			return lines.join('\n');
		})
		.join('\n\n');

	return [header, meta, chunks].filter(Boolean).join('\n\n');
};

export const renderEvidenceMarkdown = (bundle: any) => {
	return [
		'# Answer Evidence Export',
		`- Chat ID: ${bundle.chat_id ?? 'N/A'}`,
		`- Message ID: ${bundle.message_id ?? 'N/A'}`,
		`- Model: ${bundle.model_name ?? bundle.model_id ?? 'N/A'}`,
		`- Exported At: ${bundle.exported_at}`,
		'',
		'## Retrieval Models',
		`- Embedding Model: ${bundle.retrieval_models?.embedding_model ?? 'N/A'}`,
		`- Reranking Model: ${bundle.retrieval_models?.reranking_model ?? 'N/A'}`,
		'',
		'## RAG Params',
		'```json',
		stringifyPretty(bundle.rag_params ?? {}),
		'```',
		'',
		'## RAG Snapshot',
		'```json',
		stringifyPretty(bundle.rag_snapshot ?? {}),
		'```',
		'',
		'## Queries',
		'```json',
		stringifyPretty(bundle.queries ?? {}),
		'```',
		'',
		'## Usage',
		'```json',
		stringifyPretty(bundle.usage ?? {}),
		'```',
		'',
		'## Summary',
		'```json',
		stringifyPretty(bundle.summary ?? {}),
		'```',
		'',
		'## Evidence',
		...toSafeArray(bundle.sources).map(renderSourceMarkdown)
	].join('\n');
};

export const renderTraceMarkdown = (bundle: any) => {
	return [
		'# Answer Trace Export',
		`- Chat ID: ${bundle.chat_id ?? 'N/A'}`,
		`- Message ID: ${bundle.message_id ?? 'N/A'}`,
		`- Model: ${bundle.model?.name ?? bundle.model?.id ?? 'N/A'}`,
		`- Exported At: ${bundle.exported_at}`,
		'',
		'## Question',
		bundle.question?.content ?? '',
		'',
		'## Answer',
		bundle.answer?.content ?? '',
		'',
		'## RAG Params',
		'```json',
		stringifyPretty(bundle.rag_params ?? {}),
		'```',
		'',
		'## RAG Snapshot',
		'```json',
		stringifyPretty(bundle.rag_snapshot ?? {}),
		'```',
		'',
		'## Usage',
		'```json',
		stringifyPretty(bundle.usage ?? {}),
		'```',
		'',
		'## Summary',
		'```json',
		stringifyPretty(bundle.summary ?? {}),
		'```',
		'',
		'## Queries',
		'```json',
		stringifyPretty(bundle.queries ?? {}),
		'```',
		'',
		'## Evidence',
		...toSafeArray(bundle.sources).map(renderSourceMarkdown),
		'',
		'## Status History',
		'```json',
		stringifyPretty(bundle.status_history ?? []),
		'```',
		'',
		'## Tool Transcript',
		'```json',
		stringifyPretty(bundle.tool_transcript ?? []),
		'```'
	].join('\n');
};

const buildFileName = ({ chatId, message, suffix, extension }: any) => {
	const date = getExportDate();
	const modelSlug = slugify(message?.modelName ?? message?.model);
	return `${date}__chat-${chatId}__msg-${message?.id ?? 'message'}__${modelSlug}__${suffix}.${extension}`;
};

const triggerDownload = (content: string, mimeType: string, fileName: string) => {
	const blob = new Blob([content], { type: mimeType });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = fileName;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	setTimeout(() => URL.revokeObjectURL(url), 100);
};

export const downloadExport = ({ bundle, renderer, chatId, message, suffix, format }: any) => {
	if (format === 'markdown') {
		triggerDownload(renderer(bundle), 'text/markdown', buildFileName({ chatId, message, suffix, extension: 'md' }));
		return;
	}
	triggerDownload(stringifyPretty(bundle), 'application/json', buildFileName({ chatId, message, suffix, extension: 'json' }));
};
