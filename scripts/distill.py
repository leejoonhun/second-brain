#!/usr/bin/env python3
"""대화/자료를 log 노트로 증류하는 스크립트"""

import argparse
import re
from datetime import datetime
from pathlib import Path

# 워크스페이스 루트
ROOT = Path(__file__).parent.parent
VAULT_DIR = ROOT / "vault"
LOGS_DIR = VAULT_DIR / "logs"


def slugify(text: str) -> str:
    """제목을 파일명으로 변환"""
    text = re.sub(r"[^\w\s가-힣-]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text.lower()


def extract_wikilinks(text: str) -> list[str]:
    """텍스트에서 [[링크]] 추출"""
    return re.findall(r"\[\[([^\]]+)\]\]", text)


def create_distill_log(
    topic: str,
    content: str | None = None,
    decisions: str | None = None,
    knowledge: str | None = None,
    tasks: str | None = None,
    questions: str | None = None,
    links: list[str] | None = None,
):
    """대화 증류 로그 생성"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    slug = slugify(topic)
    # 로그 ID 생성
    log_id = f"log.{date_str}_{slug}"
    # 프론트매터
    frontmatter_lines = [
        "---",
        f"id: {log_id}",
        "type: log",
        f'title: "{date_str} — {topic}"',
        "aliases: []",
        'tags: ["log/distill"]',
        f"created: {date_str}",
        f"updated: {date_str}",
        "links: []",
        "sources: []",
        "---",
    ]
    # 본문
    body_lines = []
    body_lines.append(f"# {date_str} Distill — {topic}\n")
    if content:
        body_lines.append("## Context\n")
        body_lines.append(content.strip())
        body_lines.append("\n")
    if decisions:
        body_lines.append("## Decisions\n")
        body_lines.append(decisions.strip())
        body_lines.append("\n")
    if knowledge:
        body_lines.append("## New Knowledge\n")
        body_lines.append(knowledge.strip())
        body_lines.append("\n")
    if tasks:
        body_lines.append("## Tasks\n")
        body_lines.append(tasks.strip())
        body_lines.append("\n")
    if questions:
        body_lines.append("## Open Questions\n")
        body_lines.append(questions.strip())
        body_lines.append("\n")
    body_lines.append("## Links\n")
    if links:
        for link in links:
            body_lines.append(f"- [[{link}]]")
    else:
        body_lines.append("- ")
    body_lines.append("\n")
    # 파일 생성
    output_text = "\n".join(frontmatter_lines) + "\n" + "\n".join(body_lines)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = LOGS_DIR / f"{date_str}_{slug}.md"
    if output_path.exists():
        print(f"⚠️  파일이 이미 존재: {output_path}")
        response = input("덮어쓰시겠습니까? (y/N): ")
        if response.lower() != "y":
            print("취소되었습니다.")
            return None
    output_path.write_text(output_text, encoding="utf-8")
    print(f"✅ 생성됨: {output_path.relative_to(ROOT)}")
    print(f"   ID: {log_id}")
    return output_path


def interactive_distill():
    """대화형 증류 모드"""
    print("\n=== 대화 증류 (Interactive Distill) ===\n")
    topic = input("주제/토픽: ").strip()
    if not topic:
        print("❌ 주제는 필수입니다.")
        return
    print("\n다음 항목들을 입력하세요 (빈 줄로 종료)")
    print("(여러 줄 입력 가능, 끝나면 빈 줄에서 Enter)\n")

    def multiline_input(prompt: str) -> str | None:
        print(f"{prompt}")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        return "\n".join(lines) if lines else None

    content = multiline_input("## Context (선택):")
    decisions = multiline_input("\n## Decisions (선택):")
    knowledge = multiline_input("\n## New Knowledge (선택):")
    tasks = multiline_input("\n## Tasks (선택):")
    questions = multiline_input("\n## Questions (선택):")
    links_str = input(
        "\n## Links (쉼표 구분, 예: topic.alignment, project.qraft): "
    ).strip()
    links = [link.strip() for link in links_str.split(",") if link.strip()]
    # 본문에서 자동 추출된 링크 추가
    all_text = " ".join(filter(None, [content, decisions, knowledge, tasks, questions]))
    auto_links = extract_wikilinks(all_text)
    links.extend(auto_links)
    links = list(set(links))  # 중복 제거
    create_distill_log(
        topic=topic,
        content=content,
        decisions=decisions,
        knowledge=knowledge,
        tasks=tasks,
        questions=questions,
        links=links,
    )


def main():
    parser = argparse.ArgumentParser(
        description="대화/자료 증류 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 대화형 모드
  python distill.py
  
  # 간단한 로그
  python distill.py --topic "RAG 설계 논의"
  
  # 풀 옵션
  python distill.py --topic "KG 스키마 결정" \\
    --decisions "frontmatter에 links.rel/to 구조 채택" \\
    --knowledge "컨텍스트 팩 = 시드 + 그래프 확장 + 최근 노트" \\
    --links "topic.ontology,decision.kg_schema_v1"
        """,
    )
    parser.add_argument(
        "--topic",
        help="주제/토픽",
    )
    parser.add_argument(
        "--content",
        help="컨텍스트/배경",
    )
    parser.add_argument(
        "--decisions",
        help="결정 사항",
    )
    parser.add_argument(
        "--knowledge",
        help="새로운 지식/인사이트",
    )
    parser.add_argument(
        "--tasks",
        help="할 일 (줄바꿈은 \\n)",
    )
    parser.add_argument(
        "--questions",
        help="미결 질문들",
    )
    parser.add_argument(
        "--links",
        help="관련 노트 ID들 (쉼표 구분)",
    )
    args = parser.parse_args()
    # 인자가 없으면 대화형 모드
    if not args.topic:
        interactive_distill()
        return
    # CLI 모드
    links = [link.strip() for link in args.links.split(",")] if args.links else None
    tasks = args.tasks.replace("\\n", "\n") if args.tasks else None
    create_distill_log(
        topic=args.topic,
        content=args.content,
        decisions=args.decisions,
        knowledge=args.knowledge,
        tasks=tasks,
        questions=args.questions,
        links=links,
    )


if __name__ == "__main__":
    main()
