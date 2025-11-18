from pathlib import Path
import re
from typing import List, Tuple


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
QUESTIONS_FILE = EXAMPLES_DIR / "questions.txt"
DIGEST_FILE = EXAMPLES_DIR / "digest.txt"


def load_questions(path: Path) -> List[str]:
    """Load numbered questions from a text file.

    Returns a list of question strings (stripped of numbering).
    Expected format per line: "1. ¿Pregunta...?"
    """
    questions: List[str] = []
    if not path.exists():
        return questions

    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^\d+\.\s*(.+)$", line)
            if m:
                questions.append(m.group(1).strip())
            else:
                # If file doesn't use numbering, treat non-empty lines as questions
                questions.append(line)

    return questions


def parse_digest_for_codes_and_citations(path: Path, max_codes: int = 10, max_citations: int = 5) -> Tuple[List[str], List[str]]:
    """Parse the digest example to extract central codes (hashtags) and short citation/comments.

    The parser is tolerant: it looks for '%%TAGS%%' followed by hashtags and
    '%%COMMENT%%' markers followed by a short comment line. It also extracts
    inline hashtags.
    """
    codes: List[str] = []
    citations: List[str] = []
    if not path.exists():
        return codes, citations

    with path.open("r", encoding="utf-8") as fh:
        lines = [line.rstrip("\n") for line in fh]

    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln == "%%TAGS%%":
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                tag_line = lines[j].strip()
                found = re.findall(r"#[-_A-Za-z0-9]+", tag_line)
                for f in found:
                    code = f.lstrip("#")
                    if code not in codes:
                        codes.append(code)
                        if len(codes) >= max_codes:
                            break
            i = j
            continue

        if ln == "%%COMMENT%%":
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                comment = lines[j].strip()
                if comment and comment not in citations:
                    citations.append(comment)
                    if len(citations) >= max_citations:
                        break
            i = j
            continue

        inline_found = re.findall(r"#[-_A-Za-z0-9]+", ln)
        for f in inline_found:
            code = f.lstrip("#")
            if code not in codes:
                codes.append(code)
                if len(codes) >= max_codes:
                    break

        i += 1

    return codes, citations


class DataProvider:
    """Abstract data provider used by steps/tests."""

    def get_questions(self) -> List[str]:
        raise NotImplementedError()

    def get_codes_and_citations(self) -> Tuple[List[str], List[str]]:
        raise NotImplementedError()


class FileDataProvider(DataProvider):
    def __init__(self, questions_path: Path = QUESTIONS_FILE, digest_path: Path = DIGEST_FILE):
        self.questions_path = questions_path
        self.digest_path = digest_path

    def get_questions(self) -> List[str]:
        return load_questions(self.questions_path)

    def get_codes_and_citations(self) -> Tuple[List[str], List[str]]:
        return parse_digest_for_codes_and_citations(self.digest_path)


class MockDataProvider(DataProvider):
    def __init__(self, questions=None, codes=None, citations=None):
        self._questions = questions or []
        self._codes = codes or []
        self._citations = citations or []

    def get_questions(self) -> List[str]:
        return list(self._questions)

    def get_codes_and_citations(self) -> Tuple[List[str], List[str]]:
        return list(self._codes), list(self._citations)


# Default provider used by steps; tests can swap it via set_data_provider()
data_provider: DataProvider = FileDataProvider()


def set_data_provider(provider: DataProvider) -> None:
    global data_provider
    data_provider = provider


def use_mock_provider(questions=None, codes=None, citations=None) -> None:
    set_data_provider(MockDataProvider(questions=questions, codes=codes, citations=citations))
