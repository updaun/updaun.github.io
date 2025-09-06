---
layout: post
title: "FastAPI + LangChain으로 구축하는 LLM MSA 서비스"
date: 2025-09-06 10:00:00 +0900
categories: [FastAPI, LangChain, LLM, Microservices, AI]
tags: [FastAPI, LangChain, OpenAI, GPT, Microservices, Python, AI, Machine Learning, Vector Database, RAG]
---

FastAPI와 LangChain을 결합하여 확장 가능한 LLM(Large Language Model) 마이크로서비스 아키텍처를 구축하는 방법을 알아보겠습니다. 실제 프로덕션 환경에서 활용할 수 있는 구체적인 구현 패턴과 최적화 기법을 다룹니다.

## 🏗️ 아키텍처 개요

### MSA 구조 설계

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │   Auth Service  │    │ Vector Database │
│    (FastAPI)    │────│    (FastAPI)    │    │   (Chroma/Pinecone)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Chat Service   │    │ Embedding       │    │ Document        │
│  (LangChain)    │────│ Service         │────│ Processing      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Provider  │    │ Monitoring      │    │  Message Queue  │
│ (OpenAI/Hugging)│    │  & Logging      │    │    (Redis)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 1. 기본 프로젝트 구조

### 디렉토리 구조

```
llm-msa-service/
├── services/
│   ├── api-gateway/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── routers/
│   │   │   ├── middleware/
│   │   │   └── config/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── chat-service/
│   ├── embedding-service/
│   ├── auth-service/
│   └── document-service/
├── shared/
│   ├── models/
│   ├── utils/
│   └── config/
├── docker-compose.yml
└── k8s/
```

### 공통 의존성 설정

```python
# shared/requirements.txt
fastapi==0.104.1
langchain==0.0.335
langchain-openai==0.0.2
langchain-community==0.0.8
uvicorn[standard]==0.24.0
pydantic==2.5.0
redis==5.0.1
chromadb==0.4.18
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
prometheus-fastapi-instrumentator==6.1.0
structlog==23.2.0
httpx==0.25.2
```

## 🔧 2. API Gateway 구현

### 메인 게이트웨이 서비스

```python
# services/api-gateway/app/main.py
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import structlog
import httpx
import time
from typing import Dict, Any

from .routers import chat, documents, health
from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .config.settings import get_settings

# 로거 설정
logger = structlog.get_logger()

# FastAPI 앱 생성
app = FastAPI(
    title="LLM MSA API Gateway",
    description="Microservices Architecture for LLM Applications",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# 메트릭 수집
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# 서비스 디스커버리 설정
SERVICES = {
    "chat": "http://chat-service:8001",
    "embedding": "http://embedding-service:8002",
    "document": "http://document-service:8003",
    "auth": "http://auth-service:8004"
}

class ServiceProxy:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def forward_request(
        self, 
        service: str, 
        path: str, 
        method: str = "GET",
        data: Dict[Any, Any] = None,
        headers: Dict[str, str] = None
    ):
        """서비스로 요청 전달"""
        if service not in SERVICES:
            raise HTTPException(status_code=404, detail=f"Service {service} not found")
        
        url = f"{SERVICES[service]}{path}"
        
        try:
            start_time = time.time()
            
            response = await self.client.request(
                method=method,
                url=url,
                json=data,
                headers=headers
            )
            
            latency = time.time() - start_time
            logger.info(
                "service_request",
                service=service,
                path=path,
                status_code=response.status_code,
                latency=latency
            )
            
            return response.json() if response.headers.get("content-type") == "application/json" else response.text
            
        except httpx.RequestError as e:
            logger.error("service_request_failed", service=service, error=str(e))
            raise HTTPException(status_code=503, detail=f"Service {service} unavailable")

proxy = ServiceProxy()

# 라우터 등록
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(health.router, prefix="/health", tags=["health"])

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "LLM MSA API Gateway",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """요청 로깅 미들웨어"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        "request_processed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time
    )
    
    return response
```

### 채팅 라우터 구현

```python
# services/api-gateway/app/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from ..main import proxy
from ..middleware.auth import get_current_user

router = APIRouter()

class ChatMessage(BaseModel):
    role: str = Field(..., description="메시지 역할 (user, assistant, system)")
    content: str = Field(..., description="메시지 내용")
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str = Field(..., description="사용자 메시지")
    conversation_id: Optional[str] = None
    model: str = Field(default="gpt-3.5-turbo", description="사용할 LLM 모델")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    use_rag: bool = Field(default=False, description="RAG 기능 사용 여부")
    context_docs: Optional[List[str]] = Field(default=None, description="컨텍스트 문서 ID 목록")

class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    response: ChatMessage
    model_used: str
    tokens_used: int
    response_time: float
    sources: Optional[List[Dict[str, Any]]] = None

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """
    채팅 메시지 처리
    
    - 일반 채팅 또는 RAG 기반 질의응답 지원
    - 대화 컨텍스트 유지
    - 토큰 사용량 및 응답 시간 추적
    """
    try:
        # 대화 ID 생성 또는 기존 ID 사용
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # 채팅 서비스로 요청 전달
        chat_data = {
            "user_id": user["user_id"],
            "conversation_id": conversation_id,
            "message": request.message,
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "use_rag": request.use_rag,
            "context_docs": request.context_docs
        }
        
        response = await proxy.forward_request(
            service="chat",
            path="/generate",
            method="POST",
            data=chat_data
        )
        
        # 백그라운드에서 사용량 로깅
        background_tasks.add_task(
            log_usage, 
            user["user_id"], 
            response.get("tokens_used", 0),
            response.get("model_used", request.model)
        )
        
        return ChatResponse(**response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    user = Depends(get_current_user)
):
    """대화 히스토리 조회"""
    try:
        response = await proxy.forward_request(
            service="chat",
            path=f"/conversations/{conversation_id}/history?limit={limit}",
            method="GET"
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {str(e)}")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user = Depends(get_current_user)
):
    """대화 삭제"""
    try:
        await proxy.forward_request(
            service="chat",
            path=f"/conversations/{conversation_id}",
            method="DELETE"
        )
        
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

async def log_usage(user_id: str, tokens_used: int, model: str):
    """사용량 로깅 (백그라운드 태스크)"""
    try:
        await proxy.forward_request(
            service="auth",
            path="/usage/log",
            method="POST",
            data={
                "user_id": user_id,
                "tokens_used": tokens_used,
                "model": model,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        # 로깅 실패는 메인 기능에 영향을 주지 않음
        print(f"Usage logging failed: {e}")
```

## 🤖 3. 채팅 서비스 구현

### LangChain 기반 채팅 엔진

```python
# services/chat-service/app/main.py
from fastapi import FastAPI, HTTPException
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import redis
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

app = FastAPI(title="Chat Service", version="1.0.0")

# Redis 연결 (대화 히스토리 저장용)
redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

# Vector Database 연결 (RAG용)
embeddings = OpenAIEmbeddings()
vectorstore = Chroma(
    persist_directory="/app/data/chroma",
    embedding_function=embeddings
)

class TokenCounterCallback(BaseCallbackHandler):
    """토큰 사용량 추적 콜백"""
    def __init__(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
    
    def on_llm_end(self, response, **kwargs):
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            self.total_tokens = token_usage.get('total_tokens', 0)
            self.prompt_tokens = token_usage.get('prompt_tokens', 0)
            self.completion_tokens = token_usage.get('completion_tokens', 0)

class ChatEngine:
    def __init__(self):
        self.models = {
            "gpt-3.5-turbo": ChatOpenAI(model="gpt-3.5-turbo"),
            "gpt-4": ChatOpenAI(model="gpt-4"),
            "gpt-4-turbo-preview": ChatOpenAI(model="gpt-4-turbo-preview")
        }
        self.retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    async def generate_response(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_rag: bool = False,
        context_docs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """메시지에 대한 응답 생성"""
        
        start_time = time.time()
        token_callback = TokenCounterCallback()
        
        try:
            # LLM 모델 설정
            llm = self.models.get(model, self.models["gpt-3.5-turbo"])
            llm.temperature = temperature
            llm.max_tokens = max_tokens
            llm.callbacks = [token_callback]
            
            # 대화 히스토리 로드
            memory = self._load_conversation_memory(conversation_id)
            
            if use_rag:
                # RAG 기반 응답 생성
                response_text = await self._generate_rag_response(
                    message, llm, memory, context_docs
                )
            else:
                # 일반 대화 응답 생성
                response_text = await self._generate_normal_response(
                    message, llm, memory
                )
            
            # 대화 히스토리 저장
            await self._save_conversation(
                conversation_id, user_id, message, response_text
            )
            
            response_time = time.time() - start_time
            
            return {
                "conversation_id": conversation_id,
                "message": {
                    "role": "user",
                    "content": message,
                    "timestamp": time.time()
                },
                "response": {
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": time.time()
                },
                "model_used": model,
                "tokens_used": token_callback.total_tokens,
                "response_time": response_time
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Response generation failed: {str(e)}")
    
    async def _generate_rag_response(
        self,
        message: str,
        llm: ChatOpenAI,
        memory: ConversationBufferWindowMemory,
        context_docs: Optional[List[str]]
    ) -> str:
        """RAG 기반 응답 생성"""
        
        # 검색 쿼리로 관련 문서 찾기
        relevant_docs = self.retriever.get_relevant_documents(message)
        
        # 컨텍스트 구성
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # RAG 프롬프트 구성
        rag_prompt = f"""
다음 컨텍스트를 바탕으로 질문에 답하세요:

컨텍스트:
{context}

질문: {message}

답변은 컨텍스트에 기반하되, 명확하고 도움이 되도록 작성하세요.
컨텍스트에서 답을 찾을 수 없다면, 그렇다고 말씀하세요.
"""
        
        # ConversationalRetrievalChain 사용
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=self.retriever,
            memory=memory,
            return_source_documents=True
        )
        
        result = qa_chain({"question": message})
        return result["answer"]
    
    async def _generate_normal_response(
        self,
        message: str,
        llm: ChatOpenAI,
        memory: ConversationBufferWindowMemory
    ) -> str:
        """일반 대화 응답 생성"""
        
        # 시스템 메시지 설정
        system_message = SystemMessage(content="""
당신은 도움이 되고 친근한 AI 어시스턴트입니다.
사용자의 질문에 정확하고 유용한 답변을 제공하세요.
모르는 것이 있다면 솔직히 모른다고 말하세요.
""")
        
        # 대화 히스토리 가져오기
        chat_history = memory.chat_memory.messages
        
        # 메시지 구성
        messages = [system_message] + chat_history + [HumanMessage(content=message)]
        
        # 응답 생성
        response = llm(messages)
        
        # 메모리에 대화 추가
        memory.chat_memory.add_user_message(message)
        memory.chat_memory.add_ai_message(response.content)
        
        return response.content
    
    def _load_conversation_memory(self, conversation_id: str) -> ConversationBufferWindowMemory:
        """대화 히스토리 로드"""
        memory = ConversationBufferWindowMemory(
            k=10,  # 최근 10개 메시지만 유지
            return_messages=True
        )
        
        try:
            # Redis에서 대화 히스토리 로드
            history_key = f"conversation:{conversation_id}"
            messages = redis_client.lrange(history_key, -20, -1)  # 최근 20개 메시지
            
            for msg_json in messages:
                msg = json.loads(msg_json)
                if msg["role"] == "user":
                    memory.chat_memory.add_user_message(msg["content"])
                elif msg["role"] == "assistant":
                    memory.chat_memory.add_ai_message(msg["content"])
        
        except Exception as e:
            print(f"Failed to load conversation memory: {e}")
        
        return memory
    
    async def _save_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        user_message: str, 
        ai_response: str
    ):
        """대화 히스토리 저장"""
        try:
            history_key = f"conversation:{conversation_id}"
            
            # 사용자 메시지 저장
            user_msg = {
                "role": "user",
                "content": user_message,
                "timestamp": time.time(),
                "user_id": user_id
            }
            redis_client.rpush(history_key, json.dumps(user_msg))
            
            # AI 응답 저장
            ai_msg = {
                "role": "assistant",
                "content": ai_response,
                "timestamp": time.time()
            }
            redis_client.rpush(history_key, json.dumps(ai_msg))
            
            # TTL 설정 (7일)
            redis_client.expire(history_key, 604800)
            
        except Exception as e:
            print(f"Failed to save conversation: {e}")

# 채팅 엔진 인스턴스
chat_engine = ChatEngine()

# API 엔드포인트
class ChatRequest(BaseModel):
    user_id: str
    conversation_id: str
    message: str
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1000
    use_rag: bool = False
    context_docs: Optional[List[str]] = None

@app.post("/generate")
async def generate_chat_response(request: ChatRequest):
    """채팅 응답 생성"""
    return await chat_engine.generate_response(
        user_id=request.user_id,
        conversation_id=request.conversation_id,
        message=request.message,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        use_rag=request.use_rag,
        context_docs=request.context_docs
    )

@app.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: int = 50):
    """대화 히스토리 조회"""
    try:
        history_key = f"conversation:{conversation_id}"
        messages = redis_client.lrange(history_key, -limit, -1)
        
        history = []
        for msg_json in messages:
            history.append(json.loads(msg_json))
        
        return {"conversation_id": conversation_id, "messages": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """대화 삭제"""
    try:
        history_key = f"conversation:{conversation_id}"
        redis_client.delete(history_key)
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")
```

## 📄 4. 문서 처리 서비스

### 임베딩 및 벡터 저장

```python
# services/document-service/app/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
import tempfile
import os
import uuid
from typing import List, Dict, Any
from pydantic import BaseModel

app = FastAPI(title="Document Processing Service", version="1.0.0")

# 임베딩 및 벡터 저장소 설정
embeddings = OpenAIEmbeddings()
vectorstore = Chroma(
    persist_directory="/app/data/chroma",
    embedding_function=embeddings
)

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    async def process_document(
        self, 
        file: UploadFile, 
        user_id: str,
        collection_name: str = "default"
    ) -> Dict[str, Any]:
        """문서 처리 및 벡터화"""
        
        doc_id = str(uuid.uuid4())
        
        try:
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            # 문서 로드
            if file.filename.endswith('.pdf'):
                loader = PyPDFLoader(tmp_file_path)
            elif file.filename.endswith('.txt'):
                loader = TextLoader(tmp_file_path, encoding='utf-8')
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format")
            
            documents = loader.load()
            
            # 텍스트 분할
            texts = self.text_splitter.split_documents(documents)
            
            # 메타데이터 추가
            for i, text in enumerate(texts):
                text.metadata.update({
                    "document_id": doc_id,
                    "user_id": user_id,
                    "filename": file.filename,
                    "chunk_index": i,
                    "collection": collection_name
                })
            
            # 벡터 저장소에 추가
            vectorstore.add_documents(texts)
            
            # 임시 파일 정리
            os.unlink(tmp_file_path)
            
            return {
                "document_id": doc_id,
                "filename": file.filename,
                "chunks_created": len(texts),
                "collection": collection_name,
                "status": "processed"
            }
            
        except Exception as e:
            # 임시 파일 정리
            if 'tmp_file_path' in locals():
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
            
            raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
    
    async def search_documents(
        self, 
        query: str, 
        user_id: str = None,
        collection_name: str = "default",
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """문서 검색"""
        
        try:
            # 검색 필터 설정
            search_kwargs = {"k": k}
            if user_id:
                search_kwargs["filter"] = {
                    "user_id": user_id,
                    "collection": collection_name
                }
            
            # 유사도 검색
            docs = vectorstore.similarity_search_with_score(query, **search_kwargs)
            
            results = []
            for doc, score in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": float(score)
                })
            
            return results
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")

# 문서 처리기 인스턴스
doc_processor = DocumentProcessor()

# API 엔드포인트
class SearchRequest(BaseModel):
    query: str
    user_id: str = None
    collection_name: str = "default"
    k: int = 5

@app.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = "anonymous",
    collection_name: str = "default"
):
    """문서 업로드 및 처리"""
    
    # 파일 크기 제한 (10MB)
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    
    # 백그라운드에서 문서 처리
    result = await doc_processor.process_document(file, user_id, collection_name)
    
    return result

@app.post("/search")
async def search_documents(request: SearchRequest):
    """문서 검색"""
    return await doc_processor.search_documents(
        query=request.query,
        user_id=request.user_id,
        collection_name=request.collection_name,
        k=request.k
    )

@app.get("/collections/{collection_name}/documents")
async def list_documents(collection_name: str, user_id: str = None):
    """컬렉션의 문서 목록 조회"""
    try:
        # 벡터 저장소에서 메타데이터 기반 검색
        all_docs = vectorstore.get()
        
        documents = {}
        for i, metadata in enumerate(all_docs['metadatas']):
            if metadata.get('collection') == collection_name:
                if user_id is None or metadata.get('user_id') == user_id:
                    doc_id = metadata.get('document_id')
                    if doc_id not in documents:
                        documents[doc_id] = {
                            "document_id": doc_id,
                            "filename": metadata.get('filename'),
                            "user_id": metadata.get('user_id'),
                            "chunks": 0
                        }
                    documents[doc_id]["chunks"] += 1
        
        return {"documents": list(documents.values())}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str, user_id: str):
    """문서 삭제"""
    try:
        # 해당 문서의 모든 청크 삭제
        vectorstore.delete(where={"document_id": document_id, "user_id": user_id})
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
```

## 🔐 5. 인증 서비스

### JWT 기반 인증 시스템

```python
# services/auth-service/app/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import redis
import json
from typing import Optional, Dict, Any

app = FastAPI(title="Authentication Service", version="1.0.0")

# 설정
SECRET_KEY = "your-secret-key-here"  # 환경변수로 관리할 것
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Redis 연결 (토큰 관리용)
redis_client = redis.Redis(host="redis", port=6379, db=1, decode_responses=True)

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class User(BaseModel):
    user_id: str
    username: str
    email: str
    is_active: bool = True
    token_limit: int = 100000  # 월간 토큰 제한

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class AuthService:
    def __init__(self):
        # 임시 사용자 저장소 (실제로는 데이터베이스 사용)
        self.users_db = {}
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """액세스 토큰 생성"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str) -> str:
        """리프레시 토큰 생성"""
        data = {"sub": user_id, "type": "refresh"}
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        data.update({"exp": expire})
        
        refresh_token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        
        # Redis에 리프레시 토큰 저장
        redis_client.setex(
            f"refresh_token:{user_id}",
            timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            refresh_token
        )
        
        return refresh_token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """토큰 검증"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def register_user(self, user_data: UserCreate) -> User:
        """사용자 등록"""
        # 중복 확인
        if user_data.username in self.users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # 사용자 생성
        user_id = f"user_{len(self.users_db) + 1}"
        hashed_password = self.get_password_hash(user_data.password)
        
        user = User(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email
        )
        
        # 저장 (실제로는 데이터베이스에 저장)
        self.users_db[user_data.username] = {
            "user_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": hashed_password,
            "is_active": True,
            "token_limit": 100000,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return user
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """사용자 인증"""
        user_data = self.users_db.get(username)
        if not user_data:
            return None
        
        if not self.verify_password(password, user_data["hashed_password"]):
            return None
        
        return User(**user_data)
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """사용자 정보 조회"""
        for user_data in self.users_db.values():
            if user_data["user_id"] == user_id:
                return User(**user_data)
        return None

# 인증 서비스 인스턴스
auth_service = AuthService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """현재 사용자 정보 가져오기"""
    payload = auth_service.verify_token(credentials.credentials)
    user = await auth_service.get_user(payload.get("sub"))
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# API 엔드포인트
@app.post("/register", response_model=User)
async def register(user_data: UserCreate):
    """사용자 등록"""
    return await auth_service.register_user(user_data)

@app.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """로그인"""
    user = await auth_service.authenticate_user(user_data.username, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # 토큰 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.user_id, "username": user.username},
        expires_delta=access_token_expires
    )
    
    refresh_token = auth_service.create_refresh_token(user.user_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """토큰 갱신"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # Redis에서 리프레시 토큰 확인
        stored_token = redis_client.get(f"refresh_token:{user_id}")
        if stored_token != refresh_token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # 새 액세스 토큰 생성
        user = await auth_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.user_id, "username": user.username},
            expires_delta=access_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """현재 사용자 정보"""
    return current_user

@app.post("/usage/log")
async def log_usage(usage_data: dict):
    """사용량 로깅"""
    try:
        user_id = usage_data["user_id"]
        tokens_used = usage_data["tokens_used"]
        
        # 월간 사용량 업데이트
        month_key = f"usage:{user_id}:{datetime.now().strftime('%Y-%m')}"
        redis_client.incrby(month_key, tokens_used)
        redis_client.expire(month_key, timedelta(days=32))
        
        return {"message": "Usage logged successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log usage: {str(e)}")

@app.get("/usage/{user_id}")
async def get_usage(user_id: str, month: str = None):
    """사용량 조회"""
    if not month:
        month = datetime.now().strftime('%Y-%m')
    
    month_key = f"usage:{user_id}:{month}"
    usage = redis_client.get(month_key) or 0
    
    return {
        "user_id": user_id,
        "month": month,
        "tokens_used": int(usage)
    }
```

## 🐳 6. Docker 및 배포 설정

### Docker Compose 구성

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # API Gateway
  api-gateway:
    build: ./services/api-gateway
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - chat-service
      - auth-service
      - document-service
    volumes:
      - ./logs:/app/logs

  # Chat Service
  chat-service:
    build: ./services/chat-service
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    volumes:
      - chroma_data:/app/data/chroma

  # Auth Service
  auth-service:
    build: ./services/auth-service
    ports:
      - "8004:8004"
    environment:
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - redis

  # Document Service
  document-service:
    build: ./services/document-service
    ports:
      - "8003:8003"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - chroma_data:/app/data/chroma
      - ./uploads:/app/uploads

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  redis_data:
  chroma_data:
  prometheus_data:
  grafana_data:
```

### Kubernetes 배포 설정

```yaml
# k8s/api-gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  labels:
    app: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: llm-msa/api-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis:6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-service
spec:
  selector:
    app: api-gateway
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

## 🎉 결론

FastAPI와 LangChain을 활용한 LLM MSA 서비스 구축의 핵심 요소들을 살펴보았습니다.

### ✅ 주요 달성 사항

1. **확장 가능한 아키텍처**: 각 서비스별 독립적 스케일링
2. **실시간 처리**: 스트리밍 기반 채팅 및 문서 처리
3. **RAG 시스템**: 문서 기반 질의응답 구현
4. **완전한 인증**: JWT 기반 보안 시스템
5. **모니터링**: Prometheus/Grafana 연동
6. **배포 자동화**: Docker/Kubernetes 지원

### 🛠️ 실무 적용 가이드

- **단계적 도입**: 모놀리스에서 MSA로 점진적 전환
- **성능 최적화**: 캐싱과 로드 밸런싱 적용
- **비용 관리**: 토큰 사용량 모니터링 및 제한
- **보안 강화**: API 게이트웨이를 통한 중앙집중식 보안 관리

이 아키텍처를 기반으로 기업용 AI 서비스, 개인 어시스턴트, 문서 분석 시스템 등 다양한 LLM 애플리케이션을 구축할 수 있습니다. 특히 RAG 시스템을 통해 도메인 특화 지식을 활용한 고품질 응답 생성이 가능합니다.
