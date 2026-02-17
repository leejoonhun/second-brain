# Personal Knowledge Graph

파일 기반 개인 지식 그래프 시스템. Obsidian과 호환되며, LLM 컨텍스트 생성 및 대화 증류 워크플로우를 지원합니다.

## 구조

```
second-brain/
├── vault/              # 지식 노트 (Obsidian Vault)
│   ├── topics/         # 개념/주제
│   ├── orgs/           # 기업/기관
│   ├── people/         # 인물
│   ├── projects/       # 프로젝트
│   ├── decisions/      # 의사결정 기록 (ADR)
│   ├── logs/           # 일지/대화 증류
│   └── inbox/          # 분류 전 임시
├── sources/            # 원천 자료 (PDF, 웹클립 등)
├── templates/          # 노트 템플릿
├── scripts/            # 자동화 스크립트
├── prompts/            # LLM 프롬프트
└── logs/               # 컨텍스트 팩 출력
```

## 설치

```powershell
# Python 환경 (3.8+)
pip install -r requirements.txt
```

## 워크플로우

### 1. 새 노트 생성

```powershell
# 기본 사용
python scripts/new_note.py topic "벡터 검색"
python scripts/new_note.py org "OpenAI"
python scripts/new_note.py person "Jane Doe"

# 커스텀 슬러그
python scripts/new_note.py topic "Machine Learning" --slug ml
```

**지원 타입:** `topic`, `org`, `person`, `project`, `decision`, `log`

### 2. 컨텍스트 팩 생성 (질문 전)

LLM에 던질 컨텍스트를 자동으로 추출합니다.

```powershell
# 기본 (키워드 매칭)
python scripts/pack_context.py "RAG 시스템 설계 방법"

# 시드 노트 기반 확장
python scripts/pack_context.py "alignment 연구 동향" `
  --seed topic.alignment --hops 2

# 프로젝트 중심 컨텍스트
python scripts/pack_context.py "qraft 프로젝트 현황" `
  --seed project.qraft --recent-days 7

# 옵션
#   --seed: 시드 노트 ID (여러 개 가능)
#   --hops: 링크 확장 깊이 (기본: 1)
#   --recent-days: 최근 N일 노트 포함 (기본: 30)
#   --topk: 키워드 매칭 상위 N개 (기본: 10)
#   --max-tokens: 최대 토큰 (기본: 8000)
```

**출력:** `logs/contextpack_YYYYMMDD_HHMMSS_<slug>.md`

이 파일을 ChatGPT/Claude에 업로드하거나 복사해서 사용하세요.

### 3. 대화 증류 (질문 후)

대화 결과를 로그 노트로 저장합니다.

```powershell
# 대화형 모드 (추천)
python scripts/distill.py

# CLI 모드
python scripts/distill.py --topic "KG 스키마 결정" `
  --decisions "frontmatter에 links.rel/to 구조 채택" `
  --knowledge "컨텍스트 팩 = 시드 + 그래프 확장 + 최근 노트" `
  --links "topic.ontology,decision.kg_schema_v1"
```

**출력:** `vault/logs/YYYY-MM-DD_<slug>.md`

## 노트 스키마

모든 노트는 YAML frontmatter를 사용합니다:

```yaml
---
id: topic.vector_search # 고유 ID (타입.슬러그)
type: topic # topic|org|person|project|decision|log
title: "벡터 검색"
aliases: ["semantic search"]
tags: ["ai/search", "rag"]
created: 2026-02-17
updated: 2026-02-17
links: # 명시적 관계
  - rel: related_to
    to: topic.embedding
  - rel: used_in
    to: project.personal_kg
sources: [] # 원천 자료
confidence: high # high|medium|low
---
## Summary
...
```

### 권장 섹션

- **topic:** Summary, Key Points, Mental Model, Practical
- **org:** Summary, Relevance, Notes
- **person:** Summary, Context, Key Insights
- **project:** Summary, Goals, Stack & Tools, Current Status
- **decision:** Context, Decision, Rationale, Alternatives, Consequences
- **log:** Summary, Decisions, New Knowledge, Tasks, Questions

## 팁

### Obsidian 연동

`vault/` 폴더를 Obsidian Vault로 열면:

- 백링크 자동 추적
- 그래프 뷰
- 태그/검색
- 플러그인 (Dataview, Templater 등)

### 컨텍스트 팩 최적화

1. **시드 선택:** 질문과 직접 관련된 노트 1~2개
2. **hops:** 보통 1~2가 적당 (너무 많으면 노이즈)
3. **recent-days:** 프로젝트 진행 중이면 7~14일
4. **max-tokens:** 모델 컨텍스트 창의 30~50% 권장

### 링크 규칙

`links.rel`로 관계를 명시하면 나중에 진짜 KG로 확장 가능:

```yaml
links:
  - rel: related_to # 관련됨
    to: topic.embedding
  - rel: uses # 사용함
    to: topic.vector_db
  - rel: used_in # ~에 사용됨
    to: project.rag_system
  - rel: contrasts_with # 대조됨
    to: topic.lexical_search
  - rel: works_at # (person) 근무
    to: org.anthropic
  - rel: decided_in # 결정됨
    to: decision.schema_v1
```

## 확장 가능성

### 현재 (파일 기반)

- ✅ 사람이 읽고 쓰기 편함
- ✅ Git 버전 관리
- ✅ Obsidian 호환
- ✅ 키워드 + 그래프 검색

### 향후 (옵션)

- 🔲 벡터 임베딩 (Chroma/Qdrant)
- 🔲 하이브리드 검색 (키워드 + 시맨틱)
- 🔲 Property Graph DB (Neo4j/Memgraph)
- 🔲 LlamaIndex PropertyGraphIndex
- 🔲 자동 태그/링크 추천

## 원칙

1. **원자적 노트:** 한 파일 = 한 개념/사람/프로젝트
2. **ID 고정:** 제목 바뀌어도 ID는 유지
3. **Raw ↔ Distilled 분리:** 원문(sources)과 요약(vault) 분리
4. **명시적 > 자동:** 확신하는 링크만 links에, 추론은 별도
5. **번들로 주입:** vault 전체가 아닌 컨텍스트 팩만 LLM에

## 라이선스

개인 사용 목적

---

**만든 사람:** GitHub Copilot (Claude Sonnet 4.5)
**날짜:** 2026-02-17
