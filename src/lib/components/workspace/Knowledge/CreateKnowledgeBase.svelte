<script>
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { user } from '$lib/stores';
	import { createNewKnowledge } from '$lib/apis/knowledge';
	import { getRAGConfig } from '$lib/apis/retrieval';

	import AccessControl from '../common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	let loading = false;

	let name = '';
	let description = '';
	let accessControl = {};

	// RAG chunking parameters
	let chunkSize = null;
	let chunkOverlap = null;
	let textSplitter = '';
	let enableMarkdownSplitting = '';
	let showAdvancedSettings = false;

	// Default values from global config
	let defaultChunkSize = 1000;
	let defaultChunkOverlap = 100;
	let defaultTextSplitter = 'character';
	let defaultEnableMarkdownSplitting = false;

	onMount(async () => {
		// Fetch global RAG config to show default values
		try {
			const config = await getRAGConfig(localStorage.token);
			if (config) {
				defaultChunkSize = config.CHUNK_SIZE || 1000;
				defaultChunkOverlap = config.CHUNK_OVERLAP || 100;
				defaultTextSplitter = config.TEXT_SPLITTER || 'character';
				defaultEnableMarkdownSplitting = config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER || false;
			}
		} catch (e) {
			console.error('Failed to fetch RAG config:', e);
		}
	});

	const submitHandler = async () => {
		loading = true;

		if (name.trim() === '' || description.trim() === '') {
			toast.error($i18n.t('Please fill in all fields.'));
			name = '';
			description = '';
			loading = false;
			return;
		}

		const res = await createNewKnowledge(
			localStorage.token,
			name,
			description,
			accessControl,
			chunkSize,
			chunkOverlap,
			textSplitter || null,
			enableMarkdownSplitting === '' ? null : (enableMarkdownSplitting === 'true')
		).catch((e) => {
			toast.error(`${e}`);
		});

		if (res) {
			toast.success($i18n.t('Knowledge created successfully.'));
			goto(`/workspace/knowledge/${res.id}`);
		}

		loading = false;
	};
</script>

<div class="w-full max-h-full">
	<button
		class="flex space-x-1"
		on:click={() => {
			goto('/workspace/knowledge');
		}}
	>
		<div class=" self-center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					fill-rule="evenodd"
					d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
		<div class=" self-center font-medium text-sm">{$i18n.t('Back')}</div>
	</button>

	<form
		class="flex flex-col max-w-lg mx-auto mt-10 mb-10"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div class=" w-full flex flex-col justify-center">
			<div class=" text-2xl font-medium font-primary mb-2.5">
				{$i18n.t('Create a knowledge base')}
			</div>

			<div class="w-full flex flex-col gap-2.5">
				<div class="w-full">
					<div class=" text-sm mb-2">{$i18n.t('What are you working on?')}</div>

					<div class="w-full mt-1">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							bind:value={name}
							placeholder={$i18n.t('Name your knowledge base')}
							required
						/>
					</div>
				</div>

				<div>
					<div class="text-sm mb-2">{$i18n.t('What are you trying to achieve?')}</div>

					<div class=" w-full mt-1">
						<textarea
							class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							rows="4"
							bind:value={description}
							placeholder={$i18n.t('Describe your knowledge base and objectives')}
							required
						/>
					</div>
				</div>

				<!-- Advanced RAG Settings -->
				<div class="mt-2">
					<button
						type="button"
						class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
						on:click={() => (showAdvancedSettings = !showAdvancedSettings)}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4 transition-transform {showAdvancedSettings ? 'rotate-90' : ''}"
						>
							<path
								fill-rule="evenodd"
								d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
								clip-rule="evenodd"
							/>
						</svg>
						<span>{$i18n.t('Advanced RAG Settings (Optional)')}</span>
					</button>

					{#if showAdvancedSettings}
						<div class="mt-3 space-y-3 p-4 bg-gray-50 dark:bg-gray-850 rounded-lg">
							<div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
								{$i18n.t(
									'Configure chunking parameters for this knowledge base. Leave empty to use global defaults.'
								)}
							</div>

							<div class="grid grid-cols-2 gap-3">
								<div>
									<label class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">
										{$i18n.t('Chunk Size')}
										<span class="text-gray-500 dark:text-gray-400 font-normal">
											(default: {defaultChunkSize})
										</span>
									</label>
									<input
										type="number"
										class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 outline-hidden"
										bind:value={chunkSize}
										placeholder={defaultChunkSize.toString()}
										min="1"
										max="100000"
									/>
								</div>

								<div>
									<label class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">
										{$i18n.t('Chunk Overlap')}
										<span class="text-gray-500 dark:text-gray-400 font-normal">
											(default: {defaultChunkOverlap})
										</span>
									</label>
									<input
										type="number"
										class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 outline-hidden"
										bind:value={chunkOverlap}
										placeholder={defaultChunkOverlap.toString()}
										min="0"
										max="10000"
									/>
								</div>
							</div>

							<div>
								<label class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">
									{$i18n.t('Enable Markdown Header Splitting')}
									<span class="text-gray-500 dark:text-gray-400 font-normal">
										(default: {defaultEnableMarkdownSplitting ? 'Enabled' : 'Disabled'})
									</span>
								</label>
								<select
									class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 outline-hidden"
									bind:value={enableMarkdownSplitting}
								>
									<option value="">{$i18n.t('Use Global Default')}</option>
									<option value="true">{$i18n.t('Enable')}</option>
									<option value="false">{$i18n.t('Disable')}</option>
								</select>
								<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
									{$i18n.t('Split documents by markdown headers (#, ##, ###) before chunking')}
								</p>
							</div>

							<div>
								<label class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">
									{$i18n.t('Text Splitter')}
									<span class="text-gray-500 dark:text-gray-400 font-normal">
										(default: {defaultTextSplitter})
									</span>
								</label>
								<select
									class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 outline-hidden"
									bind:value={textSplitter}
								>
									<option value="">{$i18n.t('Use Global Default')}</option>
									<option value="character">{$i18n.t('Character')}</option>
									<option value="token">{$i18n.t('Token (Tiktoken)')}</option>
								</select>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div class="mt-2">
			<AccessControl
				bind:accessControl
				accessRoles={['read', 'write']}
				share={$user?.permissions?.sharing?.knowledge || $user?.role === 'admin'}
				sharePublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
			/>
		</div>

		<div class="flex justify-end mt-2">
			<div>
				<button
					class=" text-sm px-4 py-2 transition rounded-lg {loading
						? ' cursor-not-allowed bg-gray-100 dark:bg-gray-800'
						: ' bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800'} flex"
					type="submit"
					disabled={loading}
				>
					<div class=" self-center font-medium">{$i18n.t('Create Knowledge')}</div>

					{#if loading}
						<div class="ml-1.5 self-center">
							<Spinner />
						</div>
					{/if}
				</button>
			</div>
		</div>
	</form>
</div>
