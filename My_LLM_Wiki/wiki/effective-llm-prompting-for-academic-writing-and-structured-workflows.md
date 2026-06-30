---
title: "Effective LLM Prompting for Academic Writing and Structured Workflows"
created: 2023-10-27
updated: 2023-10-27
tags: ["#LLMPrompts", "#QualityOutput", "#ResearchPaper", "#Workflow", "#PromptEngineering", "#AcademicWriting"]
---

This document outlines best practices for interacting with Language Models (LLMs) to achieve high-quality outputs, particularly in the context of [[academic writing]] like [[thesis drafting]]. It contrasts vague requests with specific, structured prompts and introduces a phased approach for complex tasks.

## The Problem with Vague Requests

Vague requests, such as simply asking an LLM to "write it," often lead to unclear results that are difficult to verify or use effectively. The output quality suffers because the model lacks sufficient context and specific instructions.

### [[Bad Request Example]]

"논문 초안을 써줘" (Write me a paper draft)

### [[Good Request Example]]

"논문 제목: X. 초록과 5개의 섹션(서론, 방법, 결과, 논의, 결론) 초안을 작성해. 각 섹션마다 최소 1개의 참고문헌을 APA 형식으로 기재하고, 논리 흐름을 점검해줘."

This specific request provides:
*   A clear [[Thesis Title]] (X).
*   Required sections: [[Abstract]], [[Introduction]], [[Methods]], [[Results]], [[Discussion]], [[Conclusion]].
*   Minimum [[Reference]] requirement (at least 1 per section).
*   Required [[Citation Format]] ([[APA Format]]).
*   An explicit instruction to check for [[Logical Flow]].

## Core Principle of Quality

A fundamental principle for ensuring high-quality output from any model, including LLMs, is that:

**Quality stems not from the model itself, but from the '[[Scope of Work]], [[Inspection Criteria]], and [[Boundary of Authority]].'**

This implies that defining clear parameters for the task, setting explicit standards for evaluation, and understanding the model's capabilities and limitations are crucial for achieving desired results.

## [[Step-by-Step Paper Drafting Workflow]]

For practical applications, especially for complex tasks like drafting an entire thesis, it is recommended to break down the process into [[sequential modes]] rather than attempting to complete the entire paper at once. This approach, suggested by user `gyu_in_black`, involves the following stages:

1.  **[[Literature Search Mode]]**:
    *   Focus: [[Keyword]] research, [[Paper collection]], and organization of relevant documents.
2.  **[[Draft Creation Mode]]**:
    *   Focus: Structuring each individual [[section]] of the paper.
3.  **[[Verification Mode]]**:
    *   Focus: Checking the consistency of [[logic]], accuracy of [[citations]], and integrity of [[data]] presented.
4.  **[[Final Organization Mode]]**:
    *   Focus: Correcting [[grammar]] and refining the overall [[style]] of the paper.

By adopting a structured approach with specific prompts and a phased workflow, users can significantly enhance the quality and reliability of LLM-generated content for academic purposes.