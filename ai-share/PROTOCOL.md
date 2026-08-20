# AI Share Protocol v0

`ai-share`는 ChatGPT와 Codex 간의 메시지 전달 및 동일 시스템의 세션 handover를 위한 경량 공유 규약이다.

이 디렉터리는 대화 기록이나 프로젝트 문서를 보관하는 장소가 아니다. 상대 시스템 또는 다음 세션이 실제로 알아야 하는 최소한의 정보만 기록한다.

## 1. Directory

프로젝트 루트를 기준으로 다음 파일을 사용한다.

```text
ai-share/
├─ PROTOCOL.md
├─ llm-to-agent.md
├─ agent-to-llm.md
├─ llm-to-llm.md
└─ agent-to-agent.md
```

- `llm-to-agent.md`: ChatGPT → Codex 메시지
- `agent-to-llm.md`: Codex → ChatGPT 메시지
- `llm-to-llm.md`: ChatGPT 세션 → 다음 ChatGPT 세션 handover
- `agent-to-agent.md`: Codex 세션 → 다음 Codex 세션 handover

모든 파일은 삭제하지 않고 계속 유지한다.

## 2. Core Principles

### 2.1 최신 상태만 유지한다

각 파일에는 최신 메시지 또는 최신 handover 하나만 유지한다.

새 내용을 기록할 때 기존 내용에 append하지 않고 파일 전체를 교체한다.

과거 기록은 Git history에 맡긴다.

> History is stored by Git. Context is curated by AI.

### 2.2 필요한 정보만 전달한다

`ai-share`에는 다음 시스템이 실제로 알아야 하는 정보만 기록한다.

포함할 수 있는 내용:

- 확정된 결정
- 구현 요청
- 중요한 제약
- 확인이 필요한 질문
- 작업 결과
- 테스트 결과
- blocker
- 다음 작업에 필요한 상태
- 세션 handover에 필요한 핵심 맥락

포함하지 않는 내용:

- 사용자와 AI가 나눈 전체 토론 과정
- 장황한 사고 과정
- 잡담
- 이미 프로젝트 문서에 존재하는 일반 설명의 반복
- 상대 시스템의 작업에 필요하지 않은 정보

긴 토론이 있었다면 토론 자체가 아니라 최종 결론과 필요한 이유만 압축해서 전달한다.

### 2.3 현재 작업에 필요한 과거 맥락만 다시 포함한다

상대 시스템에게 과거 메시지 전체를 읽도록 요구하지 않는다.

이전 결정이 현재 작업에 중요하다면 현재 메시지의 `Context`에 필요한 부분만 짧게 다시 기록한다.

## 3. Message Files

대상:

- `llm-to-agent.md`
- `agent-to-llm.md`

메시지가 없을 때도 파일은 삭제하지 않는다.

기본 상태:

```md
# AI Share

state: empty
```

새 메시지를 작성할 때 파일 전체를 다음 형식으로 교체한다.

```md
# AI Share

state: active
id: <unique-message-id>
created_at: <ISO-8601 timestamp>
type: <message-type>
reply_to: <message-id or none>

## Context

현재 메시지를 이해하는 데 꼭 필요한 기존 맥락이 있을 경우에만 작성한다.

## Message

상대 시스템에 전달할 실제 내용을 작성한다.
```

`Context`가 필요하지 않으면 생략할 수 있다.

`state: active`는 이 파일에 메시지가 존재한다는 뜻이며 미처리 상태를 의미하지 않는다. 상대가 메시지를 처리한 뒤에도 마지막 메시지는 그대로 유지한다. 다음 메시지가 생길 때 기존 내용을 교체한다.

### Message Type

기본 type은 다음을 사용한다.

- `request`
- `question`
- `result`
- `blocker`
- `info`
- `ack`

불필요하게 type을 확장하지 않는다.

### Message ID

메시지마다 고유한 `id`를 사용한다.

권장 형태:

```text
20260818T085000+0900-llm
20260818T085100+0900-agent
```

정확한 형식보다 메시지를 서로 식별할 수 있다는 점이 중요하다.

### Reply

상대 메시지에 대한 응답이면 `reply_to`에 해당 메시지의 `id`를 기록한다.

관련된 이전 메시지가 없다면 `reply_to: none`으로 기록한다.

## 4. Message Handling

메시지를 전달하는 행위와 상대 시스템을 실행하거나 알리는 행위는 별개다.

AI Share v0에서는 자동 notification이나 자동 실행을 요구하지 않는다.

기본 흐름:

```text
ChatGPT
    ↓
llm-to-agent.md 갱신 및 GitHub 반영
    ↓
사용자가 Codex에게 전달사항 확인을 요청
    ↓
Codex가 GitHub 최신본을 확인하고 작업
    ↓
agent-to-llm.md 갱신 및 GitHub 반영
    ↓
사용자가 ChatGPT에게 Agent 결과 확인을 요청
    ↓
ChatGPT가 GitHub 최신본을 읽고 검토
```

사용자는 메시지 내용을 직접 복사해서 전달할 필요가 없다. 시스템 명칭은 영어 또는 한글 표현을 자연스럽게 같은 의미로 해석한다.

예:

```text
Agent에 전달해.
에이전트에 전달해.
Codex에 전달해.
코덱스에 전달해.

LLM 전달사항 봐.
ChatGPT 전달사항 봐.
챗지피티 전달사항 봐.
GPT 전달사항 봐.
지피티 전달사항 봐.

Agent 결과 봐.
에이전트 결과 봐.
Codex 결과 봐.
코덱스 결과 봐.
```

위 표현은 예시일 뿐이며 동일한 의도의 자연어 요청도 같은 방식으로 처리한다.

### 4.1 Codex / Agent의 GitHub 동기화 의무

Codex 또는 Agent가 로컬 checkout에서 작업하는 경우, `ai-share`의 송수신 기준은 로컬 파일이 아니라 **GitHub remote의 최신 상태**이다.

사용자가 LLM/ChatGPT/GPT/지피티/챗지피티의 문의, 요청, 전달사항이 왔다고 알리거나 이를 확인하라고 요청하면 Agent는 다음 규칙을 따른다.

1. 로컬 `ai-share/llm-to-agent.md`만 확인해서는 안 된다.
2. 먼저 GitHub remote를 fetch하거나 GitHub의 해당 파일을 직접 조회하여 최신 `llm-to-agent.md`를 확인한다.
3. 로컬 branch가 remote보다 뒤처져 있더라도 단순히 로컬 파일을 근거로 "문의 없음" 또는 "새 메시지 없음"이라고 판단하지 않는다.
4. 안전하게 동기화할 수 있다면 local checkout을 최신 상태로 갱신한다. 미커밋 변경이나 branch divergence 때문에 동기화가 위험하면 remote의 파일을 직접 읽고 작업하며, 필요 시 그 상태를 사용자에게 알린다.

Agent가 답변 또는 작업 결과를 `agent-to-llm.md`에 기록한 경우, 로컬 파일 수정만으로 전달이 완료된 것으로 보지 않는다.

1. `agent-to-llm.md`를 Git에 commit한다.
2. 해당 commit을 GitHub remote에 push한다.
3. push 성공을 확인한 뒤에만 LLM/ChatGPT로의 회신이 완료된 것으로 간주한다.
4. push가 실패하거나 remote 반영을 확인할 수 없으면 전달 완료라고 말하지 않고 blocker로 사용자에게 알린다.

즉 Agent의 메시지 처리 기준은 다음과 같다.

> Inbound는 GitHub에서 최신본을 확인하고, Outbound는 GitHub에 반영되어야 완료된다.

### 4.2 파일 공유

1. 다른 환경에서 확인해야 하는 파일은 로컬 경로만 전달하지 않는다.
2. **GitHub 공유:** 저장소에 둘 파일은 프로젝트 내 적절한 위치에 추가하고 commit/push한 뒤 경로를 회신한다. 별도 고정 artifact 폴더는 사용하지 않는다.
3. **Google Drive 공유:** 사용자가 Google Drive 공유를 요구한 파일에 한해 `AI-Share/artifacts/`에 업로드한다.
4. Drive에 올린 경우 `agent-to-llm.md`에 artifact key, 간단한 설명, 접근 링크를 남긴다. 프로젝트별 Drive 폴더는 만들지 않는다.

자동 notification 또는 자동 실행은 향후 별도 확장으로 추가할 수 있으며 AI Share 기본 규약에는 포함하지 않는다.

## 5. Handover Files

대상:

- `llm-to-llm.md`
- `agent-to-agent.md`

handover 파일 역시 append하지 않고 최신 handover 하나만 유지한다.

handover는 상대 시스템에게 보내는 명령이 아니라 다음 세션이 현재 작업을 이어갈 수 있도록 만든 상태 snapshot이다.

권장 형식:

```md
# Session Handover

created_at: <ISO-8601 timestamp>

## Current State

현재 프로젝트 또는 작업이 어디까지 진행되었는지 기록한다.

## Decisions

이미 확정되어 다시 논의할 필요가 없는 중요한 결정을 기록한다.

## Important Constraints

다음 세션이 반드시 지켜야 하는 제약이 있을 경우 기록한다.

## Open Issues

아직 결정되지 않았거나 해결되지 않은 문제를 기록한다.

## Next

다음 세션에서 바로 이어서 수행할 작업을 기록한다.
```

내용이 없는 section은 생략할 수 있다.

handover 역시 전체 대화나 작업 기록을 남기는 용도가 아니다. 다음 세션이 불필요한 재탐색 없이 작업을 이어갈 수 있는 최소 정보만 기록한다.

사용자는 예를 들어 `ChatGPT 핸드오버 봐`, `챗지피티 핸드오버 봐`, `GPT 핸드오버 봐`, `지피티 핸드오버 봐`, `Codex 핸드오버 봐`, `코덱스 핸드오버 봐`, `Agent 핸드오버 봐`, `에이전트 핸드오버 봐`처럼 요청할 수 있다.

## 6. Git

`ai-share`는 프로젝트 repository와 함께 Git으로 관리하는 것을 기본으로 한다.

Git은 과거 메시지 및 handover 기록, 변경 시점 확인, 필요 시 이전 상태 복원을 담당한다.

별도의 장기 log, archive 또는 메시지 저장 구조를 만들지 않는 것을 기본으로 한다. 별도 보관 구조가 필요하다고 판단되면 임의로 추가하지 않고 사용자와 협의한다.

## 7. Portability

`ai-share`는 프로젝트 종류와 기술 스택에 의존하지 않아야 한다.

새 프로젝트에서는 준비된 `ai-share/` 디렉터리를 프로젝트 루트에 복사하는 것만으로 사용할 수 있어야 한다.

프로젝트별 요구사항, 개발 규칙, 아키텍처 설명 등은 `ai-share`에 넣지 않는다. 그런 정보는 해당 프로젝트의 기존 문서가 담당한다.

`PROTOCOL.md`는 가능한 한 모든 프로젝트에서 동일하게 유지한다.

## 8. System Entry Point

ChatGPT와 Codex의 개인 설정에는 다음 진입점만 두는 것을 권장한다.

```text
ChatGPT와 Codex 간 메시지 및 세션 handover에는 현재 프로젝트 루트의 ./ai-share/PROTOCOL.md를 따른다.
```

실제 AI Share 규칙의 source of truth는 각 프로젝트의 `./ai-share/PROTOCOL.md`이다.

## 9. Guiding Rule

판단이 애매할 때는 다음 기준을 사용한다.

> 이 정보가 없으면 상대 시스템 또는 다음 세션이 작업을 제대로 수행하기 어려운가?

그렇다면 기록한다. 그렇지 않다면 기록하지 않는다.
