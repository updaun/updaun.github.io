---
layout: post
title: "프롬프트 엔지니어링을 넘어서: AI 하네스 엔지니어링의 이해와 실전"
date: 2026-04-13 10:00:00 +0900
categories: [AI, Engineering, LLM]
tags: [AI, LLM, Prompt Engineering, Harness Engineering, RAG, Agent, Workflow, Production]
render_with_liquid: false
image: "/assets/img/posts/2026-04-13-ai-harness-engineering-beyond-prompt-engineering.webp"
---

AI 애플리케이션 개발이 성숙해지면서, 단순히 좋은 프롬프트를 작성하는 것만으로는 충분하지 않다는 것이 명확해졌습니다. 프로덕션 환경에서 안정적이고 확장 가능한 AI 시스템을 구축하려면 더 포괄적인 접근이 필요합니다. 바로 **하네스 엔지니어링(Harness Engineering)**입니다.

## 🤔 프롬프트 엔지니어링의 한계

프롬프트 엔지니어링은 LLM의 출력을 최적화하는 데 중점을 둡니다:

```python
# 전형적인 프롬프트 엔지니어링
prompt = """
당신은 전문 데이터 분석가입니다.
다음 데이터를 분석하고 인사이트를 제공해주세요:
{data}

분석 결과를 3가지 핵심 포인트로 요약해주세요.
"""
response = llm.generate(prompt)
```

하지만 실제 프로덕션 환경에서는 이것만으로는 부족합니다:

- ❌ **에러 핸들링**: API 장애, 타임아웃, 레이트 리밋
- ❌ **데이터 파이프라인**: 벡터 DB, 캐싱, 전처리
- ❌ **멀티 스텝 워크플로우**: 여러 LLM 호출을 조율
- ❌ **모니터링과 추적**: 비용, 레이턴시, 품질 추적
- ❌ **버전 관리**: 프롬프트, 모델, 파라미터 변경 추적
- ❌ **A/B 테스팅**: 다양한 접근법 비교

## 🔧 하네스 엔지니어링이란?

**하네스 엔지니어링**은 LLM을 중심으로 전체 애플리케이션 아키텍처를 설계하고 관리하는 체계적 접근 방식입니다. "하네스(Harness)"는 말을 제어하는 마구(馬具)에서 유래했듯이, AI 모델의 능력을 실용적이고 안정적인 시스템으로 "제어"하고 "활용"하는 것을 의미합니다.

### 핵심 원칙

1. **추상화 계층(Abstraction Layers)**
   - LLM 제공자에 독립적인 인터페이스
   - 쉽게 교체 가능한 컴포넌트

2. **관찰 가능성(Observability)**
   - 모든 LLM 호출 추적
   - 비용과 성능 모니터링

3. **신뢰성(Reliability)**
   - 재시도 로직, 폴백 전략
   - 그레이스풀 디그레이데이션

4. **확장성(Scalability)**
   - 병렬 처리, 배치 처리
   - 캐싱과 최적화

## 🏗️ 하네스 엔지니어링의 핵심 컴포넌트

### 1. LLM 라우터 (LLM Router)

비용과 성능을 고려해 최적의 모델을 선택합니다:

```python
class LLMRouter:
    def __init__(self):
        self.models = {
            'gpt-4': {'cost': 0.03, 'latency': 2.5, 'quality': 9.5},
            'gpt-3.5-turbo': {'cost': 0.002, 'latency': 0.8, 'quality': 7.5},
            'claude-3-opus': {'cost': 0.015, 'latency': 2.0, 'quality': 9.0},
            'llama-3-70b': {'cost': 0.001, 'latency': 1.2, 'quality': 7.0}
        }
    
    def route(self, task_complexity: str, budget: float, max_latency: float):
        """태스크 특성에 따라 최적 모델 선택"""
        if task_complexity == 'high' and budget > 0.01:
            return 'gpt-4'
        elif max_latency < 1.0:
            return 'gpt-3.5-turbo'
        elif budget < 0.005:
            return 'llama-3-70b'
        else:
            return 'claude-3-opus'

# 사용 예시
router = LLMRouter()
model = router.route(
    task_complexity='medium',
    budget=0.01,
    max_latency=2.0
)
```

### 2. 컨텍스트 관리자 (Context Manager)

효율적인 컨텍스트 윈도우 관리:

```python
class ContextManager:
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.compression_threshold = 0.8
    
    def optimize_context(self, messages: list, new_message: str) -> list:
        """토큰 제한을 고려한 컨텍스트 최적화"""
        current_tokens = self.count_tokens(messages + [new_message])
        
        if current_tokens > self.max_tokens * self.compression_threshold:
            # 전략 1: 오래된 메시지 요약
            messages = self.summarize_old_messages(messages)
            
            # 전략 2: 중요도 기반 필터링
            messages = self.filter_by_importance(messages)
            
            # 전략 3: 시맨틱 압축
            messages = self.semantic_compression(messages)
        
        return messages + [new_message]
    
    def semantic_compression(self, messages: list) -> list:
        """의미를 유지하면서 컨텍스트 압축"""
        # 유사한 내용 병합
        # 중복 정보 제거
        # 핵심 정보만 추출
        return compressed_messages
```

### 3. 에이전트 오케스트레이터 (Agent Orchestrator)

여러 AI 에이전트를 조율합니다:

```python
class AgentOrchestrator:
    def __init__(self):
        self.agents = {
            'research': ResearchAgent(),
            'analysis': AnalysisAgent(),
            'writer': WriterAgent(),
            'reviewer': ReviewerAgent()
        }
        self.memory = SharedMemory()
    
    async def execute_workflow(self, task: str) -> dict:
        """멀티 에이전트 워크플로우 실행"""
        results = {}
        
        # 1단계: 리서치
        research_data = await self.agents['research'].run(task)
        self.memory.store('research', research_data)
        
        # 2단계: 분석 (병렬 실행)
        analysis_tasks = [
            self.agents['analysis'].run(research_data, aspect='trend'),
            self.agents['analysis'].run(research_data, aspect='insight'),
            self.agents['analysis'].run(research_data, aspect='risk')
        ]
        analyses = await asyncio.gather(*analysis_tasks)
        
        # 3단계: 작성
        draft = await self.agents['writer'].run(
            research=research_data,
            analyses=analyses
        )
        
        # 4단계: 검토 및 개선
        final = await self.agents['reviewer'].review_and_improve(draft)
        
        return {
            'research': research_data,
            'analyses': analyses,
            'draft': draft,
            'final': final,
            'metadata': self.get_execution_metadata()
        }
```

### 4. RAG 파이프라인 (RAG Pipeline)

검색 증강 생성을 위한 체계적 접근:

```python
class RAGPipeline:
    def __init__(self, vector_db, llm, reranker):
        self.vector_db = vector_db
        self.llm = llm
        self.reranker = reranker
        self.cache = TTLCache(maxsize=1000, ttl=3600)
    
    async def query(self, question: str, top_k: int = 10) -> str:
        """하이브리드 검색 + 리랭킹 + 생성"""
        
        # 캐시 확인
        cache_key = self.hash_query(question)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 1. 하이브리드 검색
        sparse_results = await self.bm25_search(question, top_k=20)
        dense_results = await self.vector_db.search(
            self.embed(question), 
            top_k=20
        )
        
        # 2. 결과 병합
        combined = self.merge_results(sparse_results, dense_results)
        
        # 3. 리랭킹
        reranked = await self.reranker.rerank(
            query=question, 
            documents=combined, 
            top_k=top_k
        )
        
        # 4. 컨텍스트 구성
        context = self.build_context(reranked)
        
        # 5. 생성 (source 추적)
        prompt = self.build_rag_prompt(question, context)
        response = await self.llm.generate(prompt)
        
        # 6. 인용 추가
        response_with_citations = self.add_citations(response, reranked)
        
        # 캐시 저장
        self.cache[cache_key] = response_with_citations
        
        return response_with_citations
    
    def build_context(self, documents: list) -> str:
        """컨텍스트 구성 최적화"""
        # 중복 제거
        deduplicated = self.deduplicate(documents)
        
        # 청크 순서 최적화 (관련도 + 시간순)
        ordered = self.optimize_order(deduplicated)
        
        # 메타데이터 포함
        context = ""
        for doc in ordered:
            context += f"[Source: {doc.source}, Date: {doc.date}]\n"
            context += f"{doc.content}\n\n"
        
        return context
```

### 5. 관찰 가능성 레이어 (Observability Layer)

모든 LLM 작업을 추적하고 모니터링:

```python
class LLMObservability:
    def __init__(self, tracing_service, metrics_service):
        self.tracer = tracing_service
        self.metrics = metrics_service
    
    @contextmanager
    def trace_llm_call(self, operation: str, metadata: dict = None):
        """LLM 호출 추적 컨텍스트"""
        span_id = self.tracer.start_span(operation, metadata)
        start_time = time.time()
        
        try:
            yield span_id
            
            # 성공 메트릭
            latency = time.time() - start_time
            self.metrics.record('llm.success', 1)
            self.metrics.record('llm.latency', latency)
            
        except Exception as e:
            # 실패 메트릭
            self.metrics.record('llm.error', 1)
            self.tracer.add_error(span_id, e)
            raise
            
        finally:
            self.tracer.end_span(span_id)
    
    def track_costs(self, model: str, input_tokens: int, output_tokens: int):
        """비용 추적"""
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        self.metrics.record('llm.cost', cost, tags={'model': model})
        self.metrics.record('llm.tokens.input', input_tokens)
        self.metrics.record('llm.tokens.output', output_tokens)

# 사용 예시
obs = LLMObservability(tracer, metrics)

with obs.trace_llm_call('rag_query', {'user_id': user_id}):
    response = await llm.generate(prompt)
    obs.track_costs(
        model='gpt-4',
        input_tokens=len(prompt.split()),
        output_tokens=len(response.split())
    )
```

## 🎯 실전 활용 사례

### 사례 1: 고객 지원 AI 시스템

```python
class CustomerSupportHarness:
    def __init__(self):
        self.router = LLMRouter()
        self.rag = RAGPipeline(docs_db, llm, reranker)
        self.context_mgr = ContextManager(max_tokens=16000)
        self.fallback_chain = ['gpt-4', 'claude-3', 'human_handoff']
        self.obs = LLMObservability(tracer, metrics)
    
    async def handle_ticket(self, ticket: SupportTicket) -> Response:
        """지원 티켓 처리"""
        
        with self.obs.trace_llm_call('support_ticket', {'ticket_id': ticket.id}):
            # 1. 티켓 분류 (빠른 모델 사용)
            category = await self.classify_ticket(ticket.content)
            
            # 2. 관련 문서 검색
            knowledge = await self.rag.query(ticket.content)
            
            # 3. 컨텍스트 구성 (이전 대화 포함)
            context = self.context_mgr.optimize_context(
                messages=ticket.history,
                new_message=ticket.content
            )
            
            # 4. 복잡도 평가 및 모델 선택
            complexity = self.evaluate_complexity(ticket)
            model = self.router.route(
                task_complexity=complexity,
                budget=0.05,  # 티켓당 5센트 예산
                max_latency=5.0
            )
            
            # 5. 응답 생성 (재시도 로직 포함)
            response = await self.generate_with_fallback(
                model=model,
                context=context,
                knowledge=knowledge
            )
            
            # 6. 품질 검증
            if not self.validate_response(response):
                # 사람 개입 필요
                return self.escalate_to_human(ticket, response)
            
            # 7. 메트릭 기록
            self.obs.track_costs(model, input_tokens, output_tokens)
            
            return response
    
    async def generate_with_fallback(self, model, context, knowledge):
        """폴백 체인을 통한 안정적인 생성"""
        for fallback_model in self.fallback_chain:
            try:
                if fallback_model == 'human_handoff':
                    return self.create_handoff_request()
                
                response = await self.generate_response(
                    model=fallback_model,
                    context=context,
                    knowledge=knowledge,
                    timeout=10.0
                )
                
                if self.is_valid_response(response):
                    return response
                    
            except Exception as e:
                self.obs.tracer.add_error(f"Fallback to next: {e}")
                continue
        
        raise Exception("All fallback options exhausted")
```

### 사례 2: 콘텐츠 생성 파이프라인

```python
class ContentGenerationHarness:
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.quality_checker = QualityChecker()
        self.version_manager = VersionManager()
        self.ab_tester = ABTester()
    
    async def generate_blog_post(self, topic: str, target_seo: dict) -> Article:
        """SEO 최적화된 블로그 포스트 생성"""
        
        # 버전 관리 시작
        version = self.version_manager.create_version({
            'topic': topic,
            'seo_targets': target_seo,
            'timestamp': datetime.now()
        })
        
        # A/B 테스트: 두 가지 접근법 병렬 실행
        approach_a = self.orchestrator.execute_workflow(
            task=f"Write blog about {topic}",
            strategy='detailed_research_first'
        )
        
        approach_b = self.orchestrator.execute_workflow(
            task=f"Write blog about {topic}",
            strategy='outline_first'
        )
        
        results = await asyncio.gather(approach_a, approach_b)
        
        # 품질 평가
        scores = [
            self.quality_checker.score(result['final']) 
            for result in results
        ]
        
        # 최고 품질 선택
        best_idx = scores.index(max(scores))
        best_article = results[best_idx]['final']
        
        # SEO 검증
        seo_score = self.validate_seo(best_article, target_seo)
        if seo_score < 0.8:
            # SEO 개선 반복
            best_article = await self.improve_seo(best_article, target_seo)
        
        # 버전 저장
        self.version_manager.save_version(version, {
            'article': best_article,
            'scores': scores,
            'seo_score': seo_score,
            'selected_strategy': 'detailed_research_first' if best_idx == 0 else 'outline_first'
        })
        
        return best_article
```

### 사례 3: 데이터 분석 워크플로우

```python
class DataAnalysisHarness:
    def __init__(self):
        self.code_executor = SafeCodeExecutor()
        self.llm = MultiModalLLM()
        self.result_verifier = ResultVerifier()
    
    async def analyze_dataset(self, df: pd.DataFrame, question: str) -> Report:
        """데이터 분석 자동화"""
        
        # 1. 데이터 프로파일링
        profile = self.profile_dataframe(df)
        
        # 2. 분석 계획 생성
        plan = await self.llm.generate(f"""
        Dataset: {profile}
        Question: {question}
        
        Generate a step-by-step analysis plan with Python code.
        """)
        
        # 3. 단계별 실행 및 검증
        results = []
        for step in plan.steps:
            # 코드 실행 (샌드박스)
            output = self.code_executor.run(step.code, df)
            
            # 결과 검증
            if not self.result_verifier.is_valid(output):
                # 재시도 또는 수정
                output = await self.retry_with_correction(step, output)
            
            results.append(output)
        
        # 4. 시각화 생성
        visualizations = []
        for result in results:
            if result.requires_chart:
                chart = await self.generate_visualization(result)
                visualizations.append(chart)
        
        # 5. 멀티모달 리포트 생성
        report = await self.llm.generate_multimodal(
            text_context=results,
            images=visualizations,
            template='analysis_report'
        )
        
        return report
```

## 🛠️ 주요 프레임워크와 도구

### 1. LangChain / LangGraph
- 복잡한 체인과 그래프 구조 구현
- 다양한 통합 제공

### 2. LlamaIndex
- 고급 RAG 파이프라인
- 멀티모달 인덱싱

### 3. DSPy
- 프롬프트를 프로그래밍 가능한 모듈로
- 자동 최적화

### 4. AutoGen
- 멀티 에이전트 대화
- 워크플로우 자동화

### 5. LangSmith / LangFuse
- 관찰 가능성과 디버깅
- 프롬프트 버전 관리

### 6. Semantic Kernel
- Microsoft의 AI 오케스트레이션
- 플러그인 아키텍처

## 📊 모범 사례

### 1. 계층화된 아키텍처

```
┌─────────────────────────────────────┐
│   Application Layer                 │  ← 비즈니스 로직
├─────────────────────────────────────┤
│   Orchestration Layer               │  ← 워크플로우 조율
├─────────────────────────────────────┤
│   Harness Layer                     │  ← 라우팅, 캐싱, 재시도
├─────────────────────────────────────┤
│   LLM Provider Abstraction          │  ← 모델 독립적 인터페이스
├─────────────────────────────────────┤
│   Infrastructure Layer              │  ← 벡터 DB, 큐, 모니터링
└─────────────────────────────────────┘
```

### 2. 점진적 폴백 전략

```python
fallback_strategy = [
    ('gpt-4-turbo', 3, 10.0),       # (모델, 재시도, 타임아웃)
    ('gpt-4', 2, 15.0),
    ('claude-3-opus', 2, 15.0),
    ('gpt-3.5-turbo', 3, 5.0),
    ('cached_response', 1, 1.0),
    ('human_handoff', 1, None)
]
```

### 3. 비용 최적화

```python
# 캐싱 전략
- L1: 인메모리 캐시 (identical requests)
- L2: Redis 캐시 (similar requests, semantic cache)
- L3: 벡터 DB 캐시 (유사 질의)

# 배치 처리
- 여러 요청 묶어서 처리
- 비용 절감: 40-60%

# 모델 다운그레이드
- 간단한 태스크는 작은 모델
- 복잡한 태스크만 큰 모델
```

### 4. 테스팅 전략

```python
# 유닛 테스트
- 각 컴포넌트 독립 테스트
- Mock LLM 응답 사용

# 통합 테스트
- 전체 파이프라인 검증
- 실제 LLM 호출 (소량)

# 평가 데이터셋
- Golden dataset 유지
- 정기적 회귀 테스트

# A/B 테스트
- 프로덕션에서 점진적 롤아웃
- 품질/비용/레이턴시 메트릭 비교
```

## 🚀 하네스 엔지니어링 시작하기

### 1단계: 현재 상태 평가
- [ ] LLM 호출이 몇 군데 흩어져 있나?
- [ ] 에러 핸들링이 일관적인가?
- [ ] 비용과 레이턴시를 추적하고 있나?

### 2단계: 추상화 계층 도입
- [ ] LLM 제공자 통합 인터페이스 구현
- [ ] 재시도 로직과 타임아웃 추가
- [ ] 기본 로깅 추가

### 3단계: 관찰 가능성 구축
- [ ] 모든 LLM 호출 추적
- [ ] 비용 메트릭 수집
- [ ] 품질 메트릭 정의

### 4단계: 최적화
- [ ] 캐싱 전략 구현
- [ ] 모델 라우팅 로직 추가
- [ ] 컨텍스트 관리 개선

### 5단계: 고급 기능
- [ ] 멀티 에이전트 오케스트레이션
- [ ] A/B 테스팅 프레임워크
- [ ] 자동 평가 파이프라인

## 🎓 결론

하네스 엔지니어링은 단순히 "더 나은 프롬프트"를 넘어서, AI 애플리케이션을 **프로덕션 수준**으로 끌어올리는 체계적 접근 방식입니다. 

### 핵심 포인트

1. **프롬프트는 시작일 뿐**: 전체 시스템 아키텍처를 고려해야 합니다
2. **신뢰성이 핵심**: 에러 핸들링, 폴백, 모니터링은 필수입니다
3. **비용 의식**: 모든 LLM 호출은 돈입니다
4. **반복적 개선**: 메트릭을 측정하고 지속적으로 최적화합니다

프롬프트 엔지니어링이 "무엇을 물을까"라면, 하네스 엔지니어링은 "어떻게 시스템을 구축할까"입니다. 이 두 가지를 모두 마스터할 때, 비로소 강력하고 안정적인 AI 애플리케이션을 만들 수 있습니다.

---

**참고 자료**
- LangChain Documentation: https://docs.langchain.com
- LlamaIndex: https://docs.llamaindex.ai
- DSPy: https://github.com/stanfordnlp/dspy
- OpenAI Best Practices: https://platform.openai.com/docs/guides/production-best-practices

**다음 읽을거리**
- [AI 에이전트 디자인 패턴](#)
- [프로덕션 RAG 시스템 구축하기](#)
- [LLM 비용 최적화 전략](#)
