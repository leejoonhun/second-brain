#!/usr/bin/env python3
"""질문에 대한 컨텍스트 팩 생성 스크립트"""

import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import frontmatter

# 워크스페이스 루트
ROOT = Path(__file__).parent.parent
VAULT_DIR = ROOT / "vault"
LOGS_DIR = ROOT / "logs"


def load_notes():
    """Vault의 모든 노트 로드"""
    notes = []
    for filepath in VAULT_DIR.rglob("*.md"):
        try:
            post = frontmatter.load(filepath)  # type: ignore
            meta = post.metadata or {}
            notes.append(
                {
                    "path": filepath,
                    "rel_path": filepath.relative_to(ROOT),
                    "id": meta.get("id"),
                    "type": meta.get("type"),
                    "title": meta.get("title", filepath.stem),
                    "tags": meta.get("tags", []),
                    "links": meta.get("links", []),
                    "created": meta.get("created"),
                    "updated": meta.get("updated"),
                    "confidence": meta.get("confidence", "medium"),
                    "text": post.content,
                    "metadata": meta,
                }
            )
        except Exception as e:
            print(f"⚠️  파싱 실패: {filepath} - {e}")
    return notes


def extract_section(text: str, header: str) -> str:
    """특정 섹션 추출 (## Summary, ## Key Points 등)"""
    pattern = rf"^## {re.escape(header)}\s*\n(.*?)(?:\n## |\Z)"
    match = re.search(pattern, text, flags=re.S | re.M)
    if match:
        return match.group(1).strip()
    return ""


def score_note(note: dict[str, Any], query_terms: list[str]) -> float:
    """노트의 질문 관련도 점수 계산"""
    text = (note["title"] + "\n" + note["text"]).lower()
    score = 0.0
    # 제목 매치 (가중치 3배)
    title_lower = note["title"].lower()
    for term in query_terms:
        if term in title_lower:
            score += 3.0
    # 본문 매치
    for term in query_terms:
        score += text.count(term)
    # 태그 매치 (가중치 2배)
    tags_str = " ".join(note["tags"]).lower()
    for term in query_terms:
        if term in tags_str:
            score += 2.0
    return score


def expand_links(notes: list[dict], seed_ids: set[str], hops: int = 1) -> set[str]:
    """시드 노트로부터 N-hop 링크 확장"""
    # ID로 노트 인덱싱
    notes_by_id = {n["id"]: n for n in notes if n["id"]}
    current = seed_ids.copy()
    expanded = seed_ids.copy()
    for _ in range(hops):
        next_layer = set()
        for note_id in current:
            note = notes_by_id.get(note_id)
            if not note:
                continue
            # 링크 탐색
            for link in note["links"]:
                target = link.get("to")
                if target and target not in expanded:
                    next_layer.add(target)
        expanded.update(next_layer)
        current = next_layer
        if not current:
            break
    return expanded


def get_recent_notes(notes: list[dict], days: int = 30) -> set[str]:
    """최근 N일 이내 업데이트된 노트 ID 수집"""
    cutoff = datetime.now() - timedelta(days=days)
    recent = set()
    for note in notes:
        updated = note.get("updated")
        if not updated:
            continue
        try:
            # YAML date 파싱
            if isinstance(updated, str):
                updated_dt = datetime.strptime(updated, "%Y-%m-%d")
            else:
                updated_dt = updated
            if updated_dt >= cutoff:
                if note["id"]:
                    recent.add(note["id"])
        except Exception:
            pass
    return recent


def create_context_pack(
    question: str,
    seed_ids: list[str] | None = None,
    hops: int = 1,
    recent_days: int = 30,
    topk: int = 10,
    max_tokens: int = 8000,
):
    """컨텍스트 팩 생성"""
    print("📚 노트 로딩 중...")
    notes = load_notes()
    print(f"   총 {len(notes)}개 노트 로드됨")
    # 질문 키워드 추출
    query_terms = [
        t.lower() for t in re.findall(r"[A-Za-z가-힣0-9_]+", question) if len(t) >= 2
    ]
    print(f"🔍 키워드: {', '.join(query_terms[:10])}")
    # 후보 ID 수집
    candidate_ids = set()
    # (1) 시드 노트 + 링크 확장
    if seed_ids:
        seed_set = set(seed_ids)
        expanded = expand_links(notes, seed_set, hops)
        candidate_ids.update(expanded)
        print(f"🔗 시드 확장: {len(seed_set)} → {len(expanded)}개")
    # (2) 최근 노트
    recent = get_recent_notes(notes, recent_days)
    candidate_ids.update(recent)
    print(f"📅 최근 {recent_days}일: {len(recent)}개")
    # (3) 키워드 매칭으로 상위 topk
    scored = [(n, score_note(n, query_terms)) for n in notes]
    scored.sort(key=lambda x: x[1], reverse=True)
    for note, score in scored[:topk]:
        if note["id"] and score > 0:
            candidate_ids.add(note["id"])
    # 후보 필터링 및 정렬
    notes_by_id = {n["id"]: n for n in notes if n["id"]}
    candidate_notes = [notes_by_id[nid] for nid in candidate_ids if nid in notes_by_id]
    # 점수 재계산 및 정렬
    candidate_notes = [(n, score_note(n, query_terms)) for n in candidate_notes]
    candidate_notes.sort(key=lambda x: x[1], reverse=True)
    print(f"✅ 후보: {len(candidate_notes)}개")
    # 컨텍스트 팩 생성
    output_lines = []
    output_lines.append("# CONTEXT PACK v1\n")
    output_lines.append("## Question\n")
    output_lines.append(f"{question}\n")
    output_lines.append("\n## Constraints\n")
    output_lines.append("- 답변은 vault 스키마에 맞춰서 액션/결정/노트 링크까지 제안")
    output_lines.append("- 가능하면 기존 노트를 링크하고, 새 노트가 필요하면 제안")
    output_lines.append("\n## Relevant Notes\n")
    total_tokens = 0
    included = 0
    for note, score in candidate_notes:
        # 섹션 추출
        summary = extract_section(note["text"], "Summary")
        key_points = extract_section(note["text"], "Key Points")
        section_text = f"\n### [{note['id']}] {note['title']}\n"
        if summary:
            section_text += f"\n**Summary:**\n{summary}\n"
        if key_points:
            section_text += f"\n**Key Points:**\n{key_points}\n"
        section_text += f"\n- Type: {note['type']}"
        section_text += f"\n- Tags: {', '.join(note['tags'][:5])}"
        section_text += f"\n- Path: `{note['rel_path']}`"
        section_text += f"\n- Confidence: {note['confidence']}"
        # 링크 정보
        if note["links"]:
            links_str = ", ".join([f"`{link.get('to')}`" for link in note["links"][:5]])
            section_text += f"\n- Links: {links_str}"
        section_text += "\n"
        # 토큰 체크 (대략 1 토큰 = 4자)
        est_tokens = len(section_text) // 4
        if total_tokens + est_tokens > max_tokens and included > 3:
            print(f"⚠️  토큰 제한 도달 ({total_tokens} tokens)")
            break
        output_lines.append(section_text)
        total_tokens += est_tokens
        included += 1
    # 출력 파일 저장
    output_text = "\n".join(output_lines)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    slug = re.sub(r"[^\w가-힣]+", "_", question[:30]).strip("_")
    output_path = LOGS_DIR / f"contextpack_{timestamp}_{slug}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")
    print(f"\n✅ 생성 완료: {output_path.relative_to(ROOT)}")
    print(f"   포함된 노트: {included}개")
    print(f"   예상 토큰: ~{total_tokens}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="LLM용 컨텍스트 팩 생성기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python pack_context.py "RAG 시스템 설계 방법"
  python pack_context.py "alignment 연구 동향" --seed topic.alignment --hops 2
  python pack_context.py "qraft 프로젝트 현황" --seed project.qraft --recent-days 7
        """,
    )
    parser.add_argument(
        "question",
        help="질문 또는 주제",
    )
    parser.add_argument(
        "--seed",
        action="append",
        help="시드 노트 ID (여러 개 지정 가능: --seed id1 --seed id2)",
    )
    parser.add_argument(
        "--hops",
        type=int,
        default=1,
        help="링크 확장 깊이 (기본: 1)",
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        default=30,
        help="최근 N일 노트 포함 (기본: 30)",
    )
    parser.add_argument(
        "--topk",
        type=int,
        default=10,
        help="키워드 매칭 상위 N개 (기본: 10)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=8000,
        help="최대 토큰 수 (기본: 8000)",
    )
    args = parser.parse_args()
    create_context_pack(
        question=args.question,
        seed_ids=args.seed,
        hops=args.hops,
        recent_days=args.recent_days,
        topk=args.topk,
        max_tokens=args.max_tokens,
    )


if __name__ == "__main__":
    main()
