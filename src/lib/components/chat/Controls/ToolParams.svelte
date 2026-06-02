<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { createEventDispatcher, getContext } from 'svelte';

	const i18n: any = getContext('i18n');
	const dispatch = createEventDispatcher();

	const notifyChange = () => {
		dispatch('change');
	};

	export let ragMode = null;
	export let agentRagConfig: any = {
		allow_view_knowledge_file: false,
		allow_view_file: false,
		allow_view_note: false,
		allow_workspace_notes: false,
		allow_chat_history: false
	};

	const updateAgentRagConfig = (key: string, value: boolean) => {
		agentRagConfig = {
			...(agentRagConfig ?? {}),
			[key]: value
		};
		notifyChange();
	};
	const getChecked = (event: Event) => (event.currentTarget as HTMLInputElement).checked;

	$: if (agentRagConfig) {
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
	}
</script>

<div class="space-y-1 text-xs">
	<div class="text-[11px] text-gray-500 dark:text-gray-400 pb-1">
		{$i18n.t('These settings control built-in Open WebUI tools only. Open Terminal file tools are configured separately.')}
		{#if ragMode === 'disabled'}
			{$i18n.t('RAG is disabled; enabled tool permissions are still applied manually.')}
		{/if}
	</div>

	<div>
		<Tooltip content={$i18n.t('Allow the model to read full knowledge-base files. Keep this off for large books; use chunk search instead.')} placement="top-start">
			<div class="py-0.5 flex w-full justify-between">
				<div class="self-center text-xs font-medium">{$i18n.t('Allow knowledge file reading')}</div>
				<input
					type="checkbox"
					checked={agentRagConfig.allow_view_knowledge_file}
					on:change={(event) =>
						updateAgentRagConfig('allow_view_knowledge_file', getChecked(event))}
					class="cursor-pointer"
				/>
			</div>
		</Tooltip>
	</div>

	<div>
		<Tooltip content={$i18n.t('Allow the model to inspect files stored in Open WebUI, such as uploaded files or attached knowledge files. This does not control Open Terminal files.')} placement="top-start">
			<div class="py-0.5 flex w-full justify-between">
				<div class="self-center text-xs font-medium">{$i18n.t('Allow WebUI file viewing')}</div>
				<input
					type="checkbox"
					checked={agentRagConfig.allow_view_file}
					on:change={(event) =>
						updateAgentRagConfig('allow_view_file', getChecked(event))}
					class="cursor-pointer"
				/>
			</div>
		</Tooltip>
	</div>

	<div>
		<Tooltip content={$i18n.t('Allow the model to inspect notes available in the current Open WebUI attached context.')} placement="top-start">
			<div class="py-0.5 flex w-full justify-between">
				<div class="self-center text-xs font-medium">{$i18n.t('Allow WebUI note viewing')}</div>
				<input
					type="checkbox"
					checked={agentRagConfig.allow_view_note}
					on:change={(event) =>
						updateAgentRagConfig('allow_view_note', getChecked(event))}
					class="cursor-pointer"
				/>
			</div>
		</Tooltip>
	</div>

	<div>
		<Tooltip content={$i18n.t('Allow workspace note tools such as search_notes and workspace note viewing.')} placement="top-start">
			<div class="py-0.5 flex w-full justify-between">
				<div class="self-center text-xs font-medium">{$i18n.t('Allow notes workspace')}</div>
				<input
					type="checkbox"
					checked={agentRagConfig.allow_workspace_notes}
					on:change={(event) =>
						updateAgentRagConfig('allow_workspace_notes', getChecked(event))}
					class="cursor-pointer"
				/>
			</div>
		</Tooltip>
	</div>

	<div>
		<Tooltip content={$i18n.t('Allow chat history tools such as search_chats and view_chat.')} placement="top-start">
			<div class="py-0.5 flex w-full justify-between">
				<div class="self-center text-xs font-medium">{$i18n.t('Allow chat history')}</div>
				<input
					type="checkbox"
					checked={agentRagConfig.allow_chat_history}
					on:change={(event) =>
						updateAgentRagConfig('allow_chat_history', getChecked(event))}
					class="cursor-pointer"
				/>
			</div>
		</Tooltip>
	</div>
</div>
