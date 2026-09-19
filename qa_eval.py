"""
qa_eval.py
----------
LLM-as-judge evaluation for generated Q&A.

The evaluator checks whether generated answers
are actually supported by the source context.

Architecture:

    Q&A
     ↓
   Groq
     ↓
Groundedness verdict
     ↓
 Evaluation report
"""

from typing import List

from pydantic import BaseModel, Field

from langchain_groq import ChatGroq

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from pipeline import QAPair


# ---------------------------------------------------------------------------
# Evaluation schemas
# ---------------------------------------------------------------------------

class GroundednessVerdict(BaseModel):

    question: str

    verdict: str = Field(
        description=(
            "One of: 'grounded', "
            "'partially_grounded', 'ungrounded'"
        )
    )

    reasoning: str = Field(
        description=(
            "One sentence explaining the verdict"
        )
    )


class EvalReport(BaseModel):

    verdicts: List[GroundednessVerdict]

    grounded_count: int

    total_count: int

    pass_rate: float


# ---------------------------------------------------------------------------
# Groq LLM helper
# ---------------------------------------------------------------------------

def get_eval_llm() -> ChatGroq:
    """
    Groq model used as the LLM judge.
    """

    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0,
    )


# ---------------------------------------------------------------------------
# Groundedness evaluation
# ---------------------------------------------------------------------------

def evaluate_groundedness(
    qa_pairs: List[QAPair],
    source_context: str,
    llm: ChatGroq = None,
) -> EvalReport:

    """
    For each Q&A pair, ask a judge LLM whether
    the answer is actually supported by the
    source text.

    This is an LLM-as-judge evaluation.
    """

    llm = llm or get_eval_llm()

    verdicts = []

    parser = PydanticOutputParser(
        pydantic_object=GroundednessVerdict
    )

    # -----------------------------------------------------------------------
    # Evaluation prompt
    # -----------------------------------------------------------------------

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a strict fact-checker.\n\n"
            "Given a source excerpt, a question, and an answer, "
            "judge whether the answer is supported by the source.\n\n"

            "Use exactly one of these verdicts:\n"
            "- grounded: the source clearly supports the answer\n"
            "- partially_grounded: the source supports only part "
            "of the answer\n"
            "- ungrounded: the source does not support the answer\n\n"

            "Do not use outside knowledge.\n\n"

            "{format_instructions}"
        ),
        (
            "user",
            "Source excerpt:\n{source}\n\n"
            "Question: {question}\n\n"
            "Answer: {answer}"
        ),
    ])

    chain = (
        prompt
        | llm
        | parser
    )

    # -----------------------------------------------------------------------
    # Evaluate each Q&A pair
    # -----------------------------------------------------------------------

    for pair in qa_pairs:

        verdict = chain.invoke({
            "source": source_context[:4000],
            "question": pair.question,
            "answer": pair.answer,
            "format_instructions": (
                parser.get_format_instructions()
            ),
        })

        verdicts.append(verdict)

    # -----------------------------------------------------------------------
    # Calculate metrics
    # -----------------------------------------------------------------------

    grounded_count = sum(
        1
        for v in verdicts
        if v.verdict == "grounded"
    )

    total = len(verdicts)

    pass_rate = (
        round(grounded_count / total, 2)
        if total
        else 0.0
    )

    return EvalReport(
        verdicts=verdicts,
        grounded_count=grounded_count,
        total_count=total,
        pass_rate=pass_rate,
    )


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------

def print_report(report: EvalReport):

    print("\n" + "=" * 50)
    print("GROUNDEDNESS EVAL REPORT")
    print("=" * 50)

    print(
        f"Pass rate: "
        f"{report.pass_rate * 100:.0f}% "
        f"({report.grounded_count}/"
        f"{report.total_count} grounded)\n"
    )

    for v in report.verdicts:

        marker = (
            "✓"
            if v.verdict == "grounded"
            else "✗"
        )

        print(
            f"[{marker}] "
            f"{v.verdict.upper()}: "
            f"{v.question}"
        )

        print(
            f"    → {v.reasoning}\n"
        )


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print(
        "This module is meant to be imported. "
        "See app.py — after generating a report, "
        "use the 'Run groundedness eval' button, "
        "which calls evaluate_groundedness() on "
        "the auto-generated Q&A pairs."
    )