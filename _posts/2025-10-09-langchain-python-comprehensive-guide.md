---
layout: post
title: "LangChain Python 완벽 가이드: 실전 예제로 배우는 LLM 애플리케이션 개발"
date: 2025-10-09 14:00:00 +0900
categories: [LangChain, Python, LLM, AI]
tags: [LangChain, Python, OpenAI, GPT, LLM, AI, Chain, Agent, Vector Store, RAG]
author: "updaun"
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-10-09-langchain-python-comprehensive-guide.webp"
---

LangChain은 LLM(Large Language Model)을 활용한 애플리케이션 개발을 위한 강력한 Python 프레임워크입니다. 이 가이드에서는 LangChain의 핵심 개념부터 실전 활용법까지 단계별로 살펴보겠습니다.

## 🚀 LangChain이란?

LangChain은 언어 모델을 중심으로 한 애플리케이션을 구축하기 위한 프레임워크입니다. 주요 특징:

- **모듈성**: 다양한 컴포넌트를 조합하여 복잡한 워크플로우 구성
- **체이닝**: 여러 단계의 처리를 연결하여 복잡한 작업 수행
- **에이전트**: 자율적으로 도구를 사용하는 AI 에이전트 구현
- **메모리**: 대화 기록과 컨텍스트 관리

## 📦 설치 및 기본 설정

### 1. 필수 패키지 설치

```bash
# 기본 LangChain 설치
pip install langchain

# OpenAI 통합
pip install langchain-openai

# 벡터 스토어 (Chroma)
pip install langchain-chroma

# 추가 유틸리티
pip install langchain-community
pip install langchain-experimental
```

### 2. 환경 설정

```python
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정
os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
```

## 🔧 핵심 컴포넌트

### 1. LLMs와 Chat Models

```python
from langchain_openai import OpenAI, ChatOpenAI

# 기본 LLM
llm = OpenAI(temperature=0.7)
response = llm.invoke("Python에서 리스트와 튜플의 차이점은?")
print(response)

# Chat Model (대화형)
chat = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
messages = [
    ("system", "당신은 친절한 Python 튜터입니다."),
    ("human", "Python 데코레이터에 대해 설명해주세요.")
]
response = chat.invoke(messages)
print(response.content)
```

### 2. 프롬프트 템플릿

```python
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate

# 기본 프롬프트 템플릿
prompt = PromptTemplate(
    input_variables=["topic", "level"],
    template="""
    {topic}에 대해 {level} 수준으로 설명해주세요.
    구체적인 예제와 함께 설명해주시면 좋겠습니다.
    """
)

# 사용법
formatted_prompt = prompt.format(topic="비동기 프로그래밍", level="초급자")

# Chat 프롬프트 템플릿
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 전문 프로그래밍 강사입니다."),
    ("human", "{topic}에 대해 {level} 수준으로 설명해주세요.")
])

# 체인과 결합
chain = chat_prompt | chat
response = chain.invoke({
    "topic": "함수형 프로그래밍", 
    "level": "중급자"
})
```

### 3. 출력 파서

```python
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

# JSON 출력 파서
class CodeReview(BaseModel):
    strengths: list = Field(description="코드의 장점들")
    weaknesses: list = Field(description="개선할 점들")
    suggestions: list = Field(description="개선 제안사항")

parser = JsonOutputParser(pydantic_object=CodeReview)

prompt = PromptTemplate(
    template="""
    다음 Python 코드를 리뷰해주세요:
    {code}
    
    {format_instructions}
    """,
    input_variables=["code"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

chain = prompt | llm | parser

code_sample = """
def calculate_average(numbers):
    return sum(numbers) / len(numbers)
"""

result = chain.invoke({"code": code_sample})
print(result)
```

## 🔗 체인(Chains) 활용

### 1. 기본 체인

```python
from langchain_core.runnables import RunnablePassthrough

# 간단한 체인
simple_chain = prompt | llm | StrOutputParser()

# 복잡한 체인
def analyze_code(inputs):
    code = inputs["code"]
    # 코드 분석 로직
    return {"analysis": f"분석 결과: {code}", "code": code}

complex_chain = (
    RunnablePassthrough.assign(analysis=analyze_code) |
    prompt |
    llm |
    parser
)
```

### 2. 조건부 체인

```python
from langchain_core.runnables import RunnableBranch

def route_question(inputs):
    question = inputs["question"]
    if "디버깅" in question:
        return "debug_chain"
    elif "최적화" in question:
        return "optimize_chain"
    else:
        return "general_chain"

debug_prompt = PromptTemplate.from_template(
    "디버깅 전문가로서 다음 문제를 해결해주세요: {question}"
)

optimize_prompt = PromptTemplate.from_template(
    "성능 최적화 전문가로서 다음을 개선해주세요: {question}"
)

general_prompt = PromptTemplate.from_template(
    "Python 전문가로서 다음 질문에 답해주세요: {question}"
)

branch_chain = RunnableBranch(
    (lambda x: "디버깅" in x["question"], debug_prompt | llm),
    (lambda x: "최적화" in x["question"], optimize_prompt | llm),
    general_prompt | llm
)
```

## 🧠 메모리 관리

### 1. 대화 기록 관리

```python
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain.chains import ConversationChain

# 기본 메모리
memory = ConversationBufferMemory()

conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

# 대화 시작
response1 = conversation.predict(input="안녕하세요, Python 튜터님!")
response2 = conversation.predict(input="방금 전에 뭐라고 인사했죠?")

# 요약 메모리 (긴 대화용)
summary_memory = ConversationSummaryMemory(llm=llm)
```

### 2. 커스텀 메모리

```python
from langchain.schema import BaseMemory

class CodeHistoryMemory(BaseMemory):
    """코드 실행 기록을 저장하는 커스텀 메모리"""
    
    def __init__(self):
        self.code_history = []
        
    @property
    def memory_variables(self):
        return ["code_history"]
    
    def load_memory_variables(self, inputs):
        return {"code_history": "\n".join(self.code_history)}
    
    def save_context(self, inputs, outputs):
        if "code" in inputs:
            self.code_history.append(inputs["code"])
    
    def clear(self):
        self.code_history = []
```

## 🤖 에이전트(Agents) 구현

### 1. 기본 에이전트

```python
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_community.tools import PythonREPLTool
from langchain_core.tools import tool

# 커스텀 도구 정의
@tool
def code_analyzer(code: str) -> str:
    """Python 코드를 분석하고 복잡도를 계산합니다."""
    lines = len(code.split('\n'))
    functions = code.count('def ')
    classes = code.count('class ')
    
    complexity = "낮음" if lines < 20 else "보통" if lines < 50 else "높음"
    
    return f"""
    코드 분석 결과:
    - 라인 수: {lines}
    - 함수 수: {functions}
    - 클래스 수: {classes}
    - 복잡도: {complexity}
    """

# 도구 목록
tools = [
    PythonREPLTool(),
    code_analyzer
]

# 에이전트 프롬프트
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", """당신은 Python 개발 어시스턴트입니다.
    코드 작성, 실행, 분석을 도와주세요.
    
    사용 가능한 도구:
    - Python REPL: 코드 실행
    - code_analyzer: 코드 복잡도 분석
    """),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# 에이전트 생성
agent = create_openai_functions_agent(
    llm=chat,
    tools=tools,
    prompt=agent_prompt
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

# 에이전트 실행
result = agent_executor.invoke({
    "input": "피보나치 수열을 구하는 함수를 작성하고 실행해서 결과를 보여주세요."
})
```

### 2. 리액트(ReAct) 에이전트

```python
from langchain.agents import create_react_agent

react_prompt = """
다음 도구들을 사용하여 질문에 답하세요:

{tools}

다음 형식을 사용하세요:

Question: 답해야 할 질문
Thought: 무엇을 해야 하는지 생각
Action: 수행할 액션 [{tool_names} 중 하나]
Action Input: 액션에 대한 입력
Observation: 액션의 결과
... (이 Thought/Action/Action Input/Observation을 필요한 만큼 반복)
Thought: 이제 최종 답을 알았습니다
Final Answer: 원래 질문에 대한 최종 답

시작하세요!

Question: {input}
Thought: {agent_scratchpad}
"""

react_agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=PromptTemplate.from_template(react_prompt)
)
```

## 📚 벡터 스토어와 RAG

### 1. 문서 로딩과 처리

```python
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# 문서 로딩
loader = TextLoader("python_docs.txt")
documents = loader.load()

# 텍스트 분할
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)
texts = text_splitter.split_documents(documents)

# 임베딩 생성
embeddings = OpenAIEmbeddings()

# 벡터 스토어 생성
vectorstore = Chroma.from_documents(
    documents=texts,
    embedding=embeddings,
    persist_directory="./chroma_db"
)
```

### 2. RAG 체인 구현

```python
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# 검색기 생성
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}
)

# RAG 프롬프트
rag_prompt = ChatPromptTemplate.from_messages([
    ("system", """당신은 Python 전문가입니다. 
    주어진 컨텍스트를 바탕으로 질문에 답하세요.
    
    컨텍스트:
    {context}
    """),
    ("human", "{input}")
])

# 문서 결합 체인
document_chain = create_stuff_documents_chain(
    llm=chat,
    prompt=rag_prompt
)

# 검색 체인
retrieval_chain = create_retrieval_chain(
    retriever=retriever,
    combine_docs_chain=document_chain
)

# 질문하기
response = retrieval_chain.invoke({
    "input": "Python에서 제너레이터와 이터레이터의 차이점은?"
})
print(response["answer"])
```

## 🔄 스트리밍과 비동기

### 1. 스트리밍 응답

```python
# 스트리밍 체인
streaming_chain = prompt | chat

for chunk in streaming_chain.stream({"topic": "머신러닝", "level": "중급"}):
    print(chunk.content, end="", flush=True)
```

### 2. 비동기 처리

```python
import asyncio

async def async_chain_example():
    # 비동기 체인 실행
    result = await chat.ainvoke([
        ("human", "비동기 프로그래밍의 장점을 설명해주세요.")
    ])
    return result.content

# 실행
result = asyncio.run(async_chain_example())
```

## 🛠️ 실전 예제: 코드 리뷰 봇

```python
class CodeReviewBot:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.1)
        self.memory = ConversationBufferMemory(return_messages=True)
        
        # 코드 리뷰 프롬프트
        self.review_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 시니어 Python 개발자입니다.
            코드를 리뷰하고 다음 관점에서 피드백을 제공하세요:
            1. 코드 품질
            2. 성능
            3. 보안
            4. 가독성
            5. 베스트 프랙티스
            """),
            ("human", """
            다음 코드를 리뷰해주세요:
            
            ```python
            {code}
            ```
            
            추가 컨텍스트: {context}
            """)
        ])
        
        self.chain = self.review_prompt | self.llm | JsonOutputParser()
    
    def review_code(self, code: str, context: str = ""):
        """코드를 리뷰하고 결과를 반환합니다."""
        try:
            result = self.chain.invoke({
                "code": code,
                "context": context
            })
            return result
        except Exception as e:
            return {"error": f"리뷰 중 오류 발생: {str(e)}"}
    
    def get_suggestions(self, code: str):
        """코드 개선 제안을 제공합니다."""
        suggestion_prompt = ChatPromptTemplate.from_messages([
            ("human", f"""
            다음 코드를 개선하는 방법을 제안해주세요:
            
            ```python
            {code}
            ```
            
            개선된 코드와 설명을 함께 제공해주세요.
            """)
        ])
        
        chain = suggestion_prompt | self.llm
        return chain.invoke({}).content

# 사용 예제
bot = CodeReviewBot()

sample_code = """
def get_user_data(user_id):
    import sqlite3
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    result = cursor.fetchone()
    conn.close()
    return result
"""

review_result = bot.review_code(sample_code, "사용자 데이터 조회 함수")
suggestions = bot.get_suggestions(sample_code)

print("리뷰 결과:", review_result)
print("\n개선 제안:", suggestions)
```

## 📊 성능 최적화

### 1. 캐싱

```python
from langchain.cache import InMemoryCache
from langchain.globals import set_llm_cache

# 캐시 설정
set_llm_cache(InMemoryCache())

# 이제 동일한 질문에 대해 캐시된 응답 사용
```

### 2. 배치 처리

```python
# 여러 입력을 배치로 처리
inputs = [
    {"topic": "함수형 프로그래밍"},
    {"topic": "객체지향 프로그래밍"},
    {"topic": "비동기 프로그래밍"}
]

results = chain.batch(inputs)
```

## 🚨 오류 처리와 재시도

```python
from langchain_core.runnables import RunnableRetry
from tenacity import retry, stop_after_attempt, wait_exponential

# 재시도 로직이 있는 체인
retry_chain = RunnableRetry(
    bound=chat,
    retry=retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
)

# 커스텀 오류 처리
def handle_chain_error(error):
    print(f"체인 실행 중 오류 발생: {error}")
    return "죄송합니다. 요청을 처리할 수 없습니다."

try:
    result = chain.invoke({"input": "복잡한 질문"})
except Exception as e:
    result = handle_chain_error(e)
```

## 🎯 베스트 프랙티스

### 1. 프롬프트 설계
- 명확하고 구체적인 지시사항
- 예제 포함
- 출력 형식 명시

### 2. 체인 구성
- 모듈화된 컴포넌트
- 재사용 가능한 구조
- 오류 처리 포함

### 3. 성능 고려사항
- 적절한 캐싱 전략
- 배치 처리 활용
- 비동기 처리 고려

### 4. 보안
- API 키 안전한 관리
- 입력 검증
- 출력 필터링

## 📝 마무리

LangChain은 LLM 애플리케이션 개발을 위한 강력한 도구입니다. 이 가이드에서 다룬 내용들을 활용하여:

1. **시작하기**: 기본 컴포넌트부터 차근차근
2. **실험하기**: 다양한 체인과 에이전트 조합
3. **최적화하기**: 성능과 안정성 향상
4. **확장하기**: 실제 서비스에 적용

LangChain의 풍부한 생태계를 활용하여 혁신적인 AI 애플리케이션을 만들어보세요!

---

*이 포스트가 도움이 되셨다면 공유해주세요! LangChain에 대한 더 자세한 내용이나 특정 사용 사례에 대한 질문이 있으시면 댓글로 남겨주세요.*