#!/usr/bin/env python3
"""새 노트를 템플릿으로부터 생성하는 스크립트"""

import argparse
import re
from datetime import datetime
from pathlib import Path

# 워크스페이스 루트
ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT / "templates"
VAULT_DIR = ROOT / "vault"
# 타입별 폴더 매핑
TYPE_FOLDERS = {
    "topic": VAULT_DIR / "topics",
    "org": VAULT_DIR / "orgs",
    "person": VAULT_DIR / "people",
    "project": VAULT_DIR / "projects",
    "decision": VAULT_DIR / "decisions",
    "log": VAULT_DIR / "logs",
}


def slugify(text: str) -> str:
    """제목을 파일명으로 변환"""
    # 한글/영문/숫자/공백만 남기고 제거
    text = re.sub(r"[^\w\s가-힣-]", "", text)
    # 공백을 언더스코어로
    text = re.sub(r"\s+", "_", text.strip())
    return text.lower()


def create_note(note_type: str, title: str, slug: str | None = None):
    """노트 생성"""
    if note_type not in TYPE_FOLDERS:
        print(f"❌ 지원하지 않는 타입: {note_type}")
        print(f"   사용 가능: {', '.join(TYPE_FOLDERS.keys())}")
        return
    # 슬러그 자동 생성
    if not slug:
        slug = slugify(title)
    # 템플릿 읽기
    template_path = TEMPLATES_DIR / f"{note_type}.md"
    if not template_path.exists():
        print(f"❌ 템플릿을 찾을 수 없습니다: {template_path}")
        return
    template = template_path.read_text(encoding="utf-8")
    # 변수 치환
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    content = template.replace("{{slug}}", slug)
    content = content.replace("{{title}}", title)
    content = content.replace("{{date}}", date_str)
    # 출력 경로
    folder = TYPE_FOLDERS[note_type]
    folder.mkdir(parents=True, exist_ok=True)

    output_path = folder / f"{slug}.md"

    # 파일이 이미 존재하는 경우
    if output_path.exists():
        print(f"⚠️  파일이 이미 존재합니다: {output_path}")
        response = input("덮어쓰시겠습니까? (y/N): ")
        if response.lower() != "y":
            print("취소되었습니다.")
            return
    # 파일 생성
    output_path.write_text(content, encoding="utf-8")
    print(f"✅ 생성됨: {output_path.relative_to(ROOT)}")
    print(f"   ID: {note_type}.{slug}")


def main():
    parser = argparse.ArgumentParser(
        description="Knowledge Graph 노트 생성기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python new_note.py topic "Machine Learning"
  python new_note.py org "OpenAI" --slug openai
  python new_note.py person "John Doe"
  python new_note.py decision "Use PostgreSQL for database"
        """,
    )

    parser.add_argument(
        "type",
        choices=list(TYPE_FOLDERS.keys()),
        help="노트 타입",
    )
    parser.add_argument(
        "title",
        help="노트 제목",
    )
    parser.add_argument(
        "--slug",
        help="파일명/ID에 사용할 슬러그 (기본: 제목에서 자동 생성)",
    )

    args = parser.parse_args()
    create_note(args.type, args.title, args.slug)


if __name__ == "__main__":
    main()
