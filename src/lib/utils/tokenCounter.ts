/**
 * 简化的token计算 - 使用字符估算
 * 对于英文: 1 token ≈ 4 characters
 * 对于中文: 1 token ≈ 1.5-2 characters
 * 这里使用保守估算: 1 token ≈ 3 characters
 */
export function calculateMessageTokens(content: string): number {
	if (!content) return 0;

	// 统计中文字符数
	const chineseChars = (content.match(/[\u4e00-\u9fa5]/g) || []).length;
	// 统计其他字符数
	const otherChars = content.length - chineseChars;

	// 中文: 1.5 chars per token, 英文: 4 chars per token
	const tokens = Math.ceil(chineseChars / 1.5 + otherChars / 4);

	return tokens;
}

/**
 * 计算多条消息的总token数
 */
export function calculateContextTokens(messages: any[]): number {
	let total = 0;
	for (const msg of messages) {
		if (msg.content) {
			total += calculateMessageTokens(msg.content);
		}
	}
	return total;
}
