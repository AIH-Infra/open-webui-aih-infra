"""
人文学科研究智能体Pipeline
专为人文学科研究设计的自驱动智能体

功能特性:
1. 自动文献检索与引证追踪
2. 多视角理论框架分析
3. 渐进式深度阅读
4. 学术写作辅助
5. 批判性思维引导
"""

import json
import re
from typing import Optional, Callable, Any
from pydantic import BaseModel


class Pipeline:
    """人文学科研究Pipeline主类"""

    class Valves(BaseModel):
        """可配置参数"""
        # 基础配置
        priority: int = 0
        enable_auto_retrieval: bool = True
        enable_multi_perspective: bool = True
        enable_progressive_reading: bool = True
        enable_citation_tracking: bool = True

        # RAG配置
        retrieval_top_k: int = 5
        retrieval_threshold: float = 0.7

        # 分析深度配置
        analysis_depth: str = "deep"  # shallow, medium, deep

        # 理论框架列表
        theoretical_frameworks: str = "现象学,解释学,结构主义,后结构主义,女性主义,后殖民主义"

        # 学术写作风格
        writing_style: str = "academic"  # academic, narrative, critical

    def __init__(self):
        self.type = "filter"
        self.name = "人文学科研究助手"
        self.valves = self.Valves()

        # 会话状态管理
        self.session_states = {}

        # 研究阶段定义
        self.research_stages = [
            "问题界定",
            "文献综述",
            "理论框架",
            "深度分析",
            "批判反思",
            "综合论述"
        ]

    def get_session_state(self, user_id: str) -> dict:
        """获取会话状态"""
        if user_id not in self.session_states:
            self.session_states[user_id] = {
                "current_stage": 0,
                "research_topic": None,
                "key_concepts": [],
                "cited_sources": [],
                "theoretical_lens": [],
                "reading_history": [],
                "analysis_depth": 0,
                "writing_fragments": []
            }
        return self.session_states[user_id]

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        入口过滤器: 在消息发送给LLM前进行智能增强
        """
        print(f"[人文研究Pipeline] 入口处理开始")

        user_id = __user__.get("id", "default") if __user__ else "default"
        state = self.get_session_state(user_id)

        # 获取用户消息
        messages = body.get("messages", [])
        if not messages:
            return body

        user_message = messages[-1].get("content", "")

        # 1. 识别研究意图
        intent = self.identify_research_intent(user_message)
        print(f"[研究意图] {intent}")

        # 2. 根据意图进行不同处理
        if intent == "literature_review":
            body = self.enhance_literature_review(body, user_message, state)
        elif intent == "theoretical_analysis":
            body = self.enhance_theoretical_analysis(body, user_message, state)
        elif intent == "close_reading":
            body = self.enhance_close_reading(body, user_message, state)
        elif intent == "critical_thinking":
            body = self.enhance_critical_thinking(body, user_message, state)
        elif intent == "academic_writing":
            body = self.enhance_academic_writing(body, user_message, state)
        else:
            # 通用增强
            body = self.enhance_general_research(body, user_message, state)

        # 3. 自动调整模型参数
        body = self.auto_adjust_parameters(body, intent)

        # 4. 记录研究历史
        state["reading_history"].append({
            "message": user_message,
            "intent": intent,
            "timestamp": self.get_timestamp()
        })

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        出口过滤器: 在响应返回给用户前进行后处理
        """
        print(f"[人文研究Pipeline] 出口处理开始")

        user_id = __user__.get("id", "default") if __user__ else "default"
        state = self.get_session_state(user_id)

        messages = body.get("messages", [])
        if not messages:
            return body

        assistant_message = messages[-1].get("content", "")

        # 1. 提取关键概念
        concepts = self.extract_key_concepts(assistant_message)
        state["key_concepts"].extend(concepts)
        state["key_concepts"] = list(set(state["key_concepts"]))[:20]  # 保留最多20个

        # 2. 提取引用来源
        citations = self.extract_citations(assistant_message)
        state["cited_sources"].extend(citations)

        # 3. 生成深度追问
        follow_ups = self.generate_humanities_follow_ups(
            messages,
            state,
            assistant_message
        )
        body["follow_ups"] = follow_ups

        # 4. 添加研究进度提示
        if self.valves.enable_progressive_reading:
            progress_hint = self.generate_progress_hint(state)
            if progress_hint:
                assistant_message += f"\n\n---\n**研究进度提示**: {progress_hint}"
                messages[-1]["content"] = assistant_message

        return body

    def identify_research_intent(self, message: str) -> str:
        """识别研究意图"""
        message_lower = message.lower()

        # 文献综述相关
        if any(kw in message for kw in ["文献", "综述", "研究现状", "学术史", "前人研究"]):
            return "literature_review"

        # 理论分析相关
        if any(kw in message for kw in ["理论", "框架", "视角", "范式", "方法论"]):
            return "theoretical_analysis"

        # 细读分析相关
        if any(kw in message for kw in ["分析", "解读", "诠释", "阐释", "细读"]):
            return "close_reading"

        # 批判性思维相关
        if any(kw in message for kw in ["批判", "质疑", "反思", "局限", "问题"]):
            return "critical_thinking"

        # 学术写作相关
        if any(kw in message for kw in ["写", "论文", "文章", "段落", "论证"]):
            return "academic_writing"

        return "general_research"

    def enhance_literature_review(self, body: dict, message: str, state: dict) -> dict:
        """增强文献综述功能"""
        print("[增强] 文献综述模式")

        # 构建文献综述提示
        enhancement = f"""
[研究助手提示 - 文献综述模式]

请以学术文献综述的标准进行回答,包括:

1. **研究脉络梳理**: 追溯该主题的学术发展历程
2. **主要学派观点**: 总结不同学派的核心观点和代表学者
3. **研究方法演变**: 说明研究方法的发展变化
4. **争议焦点**: 指出学术界的主要争议点
5. **研究缺口**: 识别尚未充分研究的领域

已知关键概念: {', '.join(state['key_concepts'][:10]) if state['key_concepts'] else '无'}

---
[用户问题]
{message}
"""

        messages = body.get("messages", [])
        messages[-1]["content"] = enhancement

        return body

    def enhance_theoretical_analysis(self, body: dict, message: str, state: dict) -> dict:
        """增强理论分析功能"""
        print("[增强] 理论分析模式")

        frameworks = self.valves.theoretical_frameworks.split(",")

        enhancement = f"""
[研究助手提示 - 多视角理论分析]

请从以下理论框架进行多视角分析:
{chr(10).join(f'{i+1}. {fw.strip()}' for i, fw in enumerate(frameworks[:4]))}

对每个视角,请说明:
- 该理论如何理解这个问题
- 该理论的核心概念和分析工具
- 该理论的洞见和局限
- 不同理论之间的对话可能

当前研究主题: {state.get('research_topic', '未设定')}

---
[用户问题]
{message}
"""

        messages = body.get("messages", [])
        messages[-1]["content"] = enhancement

        return body

    def enhance_close_reading(self, body: dict, message: str, state: dict) -> dict:
        """增强细读分析功能"""
        print("[增强] 细读分析模式")

        # 增加分析深度
        state["analysis_depth"] += 1

        depth_prompts = {
            1: "请进行初步解读,关注表层意义和基本结构",
            2: "请进行深入分析,探讨隐含意义、修辞手法和文化语境",
            3: "请进行批判性诠释,揭示意识形态、权力关系和话语建构"
        }

        depth_level = min(state["analysis_depth"], 3)

        enhancement = f"""
[研究助手提示 - 细读分析 第{depth_level}层]

{depth_prompts[depth_level]}

分析维度:
1. **文本结构**: 叙事结构、论证逻辑、修辞策略
2. **语言特征**: 词汇选择、句式特点、风格特色
3. **文化语���**: 历史背景、社会语境、文化传统
4. **深层意涵**: 象征意义、隐喻系统、价值取向
5. **互文关系**: 与其他文本的对话和引用

已识别关键概念: {', '.join(state['key_concepts'][:5])}

---
[用户问题]
{message}
"""

        messages = body.get("messages", [])
        messages[-1]["content"] = enhancement

        return body

    def enhance_critical_thinking(self, body: dict, message: str, state: dict) -> dict:
        """增强批判性思维功能"""
        print("[增强] 批判性思维模式")

        enhancement = f"""
[研究助手提示 - 批判性反思]

请采用批判性思维方法,从以下角度进行质疑和反思:

1. **前提假设**: 这个观点基于什么前提?这些前提是否成立?
2. **论证逻辑**: 论证过程是否严密?是否存在逻辑漏洞?
3. **证据充分性**: 证据是否充分?是否存在反例?
4. **视角局限**: 这个观点忽略了什么?谁的声音被排除了?
5. **权力关系**: 这个观点服务于谁的利益?维护了什么权力结构?
6. **替代解释**: 是否存在其他可能的解释?

请保持学术严谨,既要批判也要建设性。

---
[用户问题]
{message}
"""

        messages = body.get("messages", [])
        messages[-1]["content"] = enhancement

        return body

    def enhance_academic_writing(self, body: dict, message: str, state: dict) -> dict:
        """增强学术写作功能"""
        print("[增强] 学术写作模式")

        enhancement = f"""
[研究助手提示 - 学术写作辅助]

请协助学术写作,遵循以下规范:

1. **论证结构**:
   - 明确的论点(thesis statement)
   - 清晰的论证链条
   - 充分的证据支持

2. **学术规范**:
   - 使用学术语言和专业术语
   - 适当引用文献(如需要)
   - 保持客观和批判性

3. **写作风格**:
   - 段落结构清晰(主题句-展开-小结)
   - 过渡自然流畅
   - 避免口语化表达

4. **引证要求**:
   - 区分直接引用和转述
   - 标注引用来源
   - 避免过度引用

已有写作片段: {len(state['writing_fragments'])}个
已引用来源: {len(state['cited_sources'])}个

---
[用户问题]
{message}
"""

        messages = body.get("messages", [])
        messages[-1]["content"] = enhancement

        return body

    def enhance_general_research(self, body: dict, message: str, state: dict) -> dict:
        """通用研究增强"""
        print("[增强] 通用研究模式")

        # 如果是研究初期,帮助界定问题
        if not state.get("research_topic"):
            enhancement = f"""
[研究助手提示]

让我们一起界定研究问题。好的研究问题应该:
1. 具有学术价值和理论意义
2. 范围适中,可以深入研究
3. 有明确的研究对象和分析角度
4. 能够产生新的洞见

请告诉我您的研究兴趣,我会帮助您:
- 梳理研究脉络
- 界定研究范围
- 提出研究问题
- 建议理论框架

---
[用户问题]
{message}
"""
            messages = body.get("messages", [])
            messages[-1]["content"] = enhancement

        return body

    def auto_adjust_parameters(self, body: dict, intent: str) -> dict:
        """根据研究意图自动调整模型参数"""

        # 不同研究意图的最佳参数配置
        param_configs = {
            "literature_review": {
                "temperature": 0.3,  # 文献综述需要准确性
                "top_p": 0.9,
                "max_tokens": 3000
            },
            "theoretical_analysis": {
                "temperature": 0.5,  # 理论分析需要平衡创造性和准确性
                "top_p": 0.92,
                "max_tokens": 3500
            },
            "close_reading": {
                "temperature": 0.6,  # 细读需要一定创造性
                "top_p": 0.93,
                "max_tokens": 3000
            },
            "critical_thinking": {
                "temperature": 0.7,  # 批判性思维需要创造性
                "top_p": 0.95,
                "max_tokens": 2500
            },
            "academic_writing": {
                "temperature": 0.4,  # 学术写作需要规范性
                "top_p": 0.9,
                "max_tokens": 4000
            }
        }

        config = param_configs.get(intent, {
            "temperature": 0.5,
            "top_p": 0.9,
            "max_tokens": 2500
        })

        body.update(config)
        print(f"[参数调整] {intent}: temp={config['temperature']}, max_tokens={config['max_tokens']}")

        return body

    def generate_humanities_follow_ups(self, messages: list, state: dict, response: str) -> list:
        """生成人文学科特色的追问"""

        follow_ups = []

        # 基于当前分析深度生成追问
        depth = state.get("analysis_depth", 0)

        if depth == 0:
            # 初步阶段:引导深入
            follow_ups = [
                "能否从不同理论视角重新审视这个问题?",
                "这个观点的历史渊源和学术脉络是什么?",
                "有哪些相关的经典文献值得参考?"
            ]
        elif depth == 1:
            # 深入阶段:多角度分析
            follow_ups = [
                "这个解释忽略了哪些重要维度?",
                "从批判性角度看,这个观点有什么局限?",
                "能否提供具体的文本证据支持这个论断?"
            ]
        else:
            # 综合阶段:理论建构
            follow_ups = [
                "如何将这些洞见整合成连贯的论述?",
                "这个分析对现有理论有什么贡献?",
                "还有哪些问题值得进一步探讨?"
            ]

        # 基于关键概念生成追问
        if state.get("key_concepts"):
            concept = state["key_concepts"][0]
            follow_ups.append(f"'{concept}'这个概念在不同语境中的含义有何差异?")

        # 基于研究阶段生成追问
        current_stage = state.get("current_stage", 0)
        if current_stage < len(self.research_stages) - 1:
            next_stage = self.research_stages[current_stage + 1]
            follow_ups.append(f"接下来进入'{next_stage}'阶段,需要关注什么?")

        return follow_ups[:5]  # 最多返回5个追问

    def extract_key_concepts(self, text: str) -> list:
        """提取关键概念"""
        # 简单实现:提取引号中的内容和专有名词
        concepts = []

        # 提取引号内容
        quoted = re.findall(r'[「『""]([^」』""]+)[」』""]', text)
        concepts.extend(quoted)

        # 提取可能的学术术语(中文2-6字,英文大写开头)
        terms = re.findall(r'[\u4e00-\u9fa5]{2,6}(?:主义|理论|方法|视角|范式)', text)
        concepts.extend(terms)

        return list(set(concepts))[:10]

    def extract_citations(self, text: str) -> list:
        """提取引用来源"""
        citations = []

        # 提取作者年份格式: (作者, 年份)
        pattern1 = re.findall(r'\(([^)]+),\s*(\d{4})\)', text)
        citations.extend([f"{author} ({year})" for author, year in pattern1])

        # 提取书名号内容
        pattern2 = re.findall(r'《([^》]+)》', text)
        citations.extend(pattern2)

        return list(set(citations))

    def generate_progress_hint(self, state: dict) -> str:
        """生成研究进度提示"""
        hints = []

        # 概念积累提示
        concept_count = len(state.get("key_concepts", []))
        if concept_count > 10:
            hints.append(f"已积累{concept_count}个关键概念,可以开始构建概念图谱")

        # 引用提示
        citation_count = len(state.get("cited_sources", []))
        if citation_count > 5:
            hints.append(f"已引用{citation_count}个来源,注意整理文献综述")

        # 分析深度提示
        depth = state.get("analysis_depth", 0)
        if depth >= 2:
            hints.append("分析已达到较深层次,可以考虑综合论述")

        return " | ".join(hints) if hints else ""

    def get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Pipeline实例化
pipeline = Pipeline()
