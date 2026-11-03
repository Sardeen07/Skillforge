---
module: llm-apps
capability: LLM applications: prompts, RAG, agents, tools, evaluation, cost and security
technologies: llm
applies: llm, prompt, rag, embeddings, vector database, agent, tool calling, evaluation, tokens
checked_against: Anthropic and OpenAI platform documentation, OWASP Top 10 for LLM Applications (2025)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## prompt-clear-instructions: Give the model explicit instructions, context and output format
tags: llm, prompt engineering, system prompt, instructions, output format, examples
keywords: vague prompt, inconsistent answers
refs: https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview

State the task, audience, constraints and success criteria explicitly; separate instructions from supplied data with clear delimiters (for example XML tags); give the exact output format; and add a few representative examples for formats that matter. Change one thing at a time and measure against an evaluation set rather than editing by feel.

## structured-outputs: Request structured output with a schema and validate it
tags: llm, structured output, json schema, tool use, parsing, validation, pydantic
keywords: model returned invalid json, regex parsing output
refs: https://docs.claude.com/en/docs/build-with-claude/structured-outputs

Do not parse free text with regexes. Use the provider's structured-output or tool-calling feature with a JSON schema, then validate the result again in code (pydantic, zod) and handle validation failure by retrying with the error message or falling back. Keep schemas small, and use enums for closed sets.

## rag-chunking: Chunk documents by structure with overlap and metadata
tags: llm, rag, chunking, retrieval augmented generation, document processing, metadata
keywords: answers miss context, chunks cut mid sentence
refs: https://docs.claude.com/en/docs/build-with-claude/retrieval-augmented-generation

Split on document structure (headings, sections, paragraphs) rather than fixed character counts, with modest overlap, and store metadata (source, title, section, date, access permissions) alongside each chunk. Prepending a short document-level context to each chunk before embedding improves retrieval of chunks that are ambiguous on their own.

## rag-hybrid-retrieval: Combine keyword and vector retrieval, then rerank
tags: llm, rag, hybrid search, bm25, vector search, reranking, embeddings, retrieval quality
keywords: vector search misses exact terms, error codes not found
refs: https://www.anthropic.com/news/contextual-retrieval

Dense embeddings miss exact identifiers (error codes, function names, SKUs) that keyword search finds, and keyword search misses paraphrases. Retrieve candidates with both (BM25 + vectors, fused with reciprocal rank fusion), rerank the top candidates with a cross-encoder or reranker, and pass only the best few chunks to the model.

## rag-evaluate-retrieval: Evaluate retrieval separately from generation
tags: llm, rag, evaluation, recall at k, retrieval metrics, golden set, groundedness
keywords: cannot tell why answer is wrong
refs: https://docs.claude.com/en/docs/test-and-evaluate/develop-tests

Build a labeled set of questions with the passages that answer them, measure retrieval recall@k and precision separately from answer quality, and measure answer groundedness (claims supported by retrieved text). Most RAG failures are retrieval failures; tuning prompts cannot fix a missing passage.

## rag-access-control: Enforce document permissions at retrieval time
tags: llm, rag, access control, authorization, multi tenant, data leakage, security
keywords: chatbot revealed another customer's document
refs: https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/

Filter retrieved chunks by the requesting user's permissions (tenant, ACL) in the vector query itself, using metadata stored at indexing time. Never rely on the prompt to tell the model to hide documents it was given: anything in the context can be repeated.

## embeddings-consistency: Use the same embedding model and preprocessing for indexing and queries
tags: llm, embeddings, vector database, model version, normalization, reindexing, similarity
keywords: search quality dropped after upgrade
refs: https://platform.openai.com/docs/guides/embeddings

Vectors from different models (or versions, or input formats) are not comparable. Store the embedding model and version with the index, re-embed everything when you change it, apply the same text normalization at index and query time, and use the similarity metric the model was trained for (often cosine on normalized vectors).

## vector-index-tuning: Choose and tune the vector index for recall and latency
tags: llm, vector database, hnsw, ivf, ann, recall, latency, pgvector, filtering
keywords: vector search slow, filtered search returns nothing
refs: https://github.com/pgvector/pgvector#indexing

Approximate indexes (HNSW, IVF) trade recall for speed; tune parameters such as HNSW `ef_search` against a measured recall target on your data. Heavy metadata filters applied after an approximate search can return too few results: use filtered/iterative search support or partition by the filter key.

## tool-definitions: Write precise tool descriptions and validate tool arguments
tags: llm, tool calling, function calling, tool use, agents, json schema, validation
keywords: model calls wrong tool, bad arguments
refs: https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview

Name tools clearly, describe when to use and not use each one, document every parameter with types, formats and examples, and keep the tool set small for the task. Treat model-produced arguments as untrusted input: validate them, and return clear, actionable error messages as tool results so the model can correct itself.

## agent-loop-limits: Bound agent loops with step, time and cost limits
tags: llm, agents, agent loop, max iterations, cost control, timeouts, termination
keywords: agent runs forever, runaway token cost
refs: https://www.anthropic.com/engineering/building-effective-agents

Agents can loop. Cap iterations, wall-clock time and tokens/spend per task, detect repeated identical tool calls, and stop with a clear status when a limit is hit. Start with the simplest workflow (a single call or a fixed chain) and add autonomy only where it measurably helps.

## agent-human-approval: Require confirmation for irreversible agent actions
tags: llm, agents, human in the loop, permissions, destructive actions, least privilege, security
keywords: agent deleted data, sent email without asking
refs: https://genai.owasp.org/llmrisk/llm062025-excessive-agency/

Give agents the minimum tools and permissions needed, scope credentials narrowly, and require explicit human approval for irreversible or external actions (payments, deletions, sending messages, deploys). Log every tool call with arguments and results for audit.

## prompt-injection-defense: Treat retrieved and tool content as untrusted data
tags: llm, prompt injection, indirect prompt injection, security, untrusted content, agents
keywords: web page told the model to ignore instructions
refs: https://genai.owasp.org/llmrisk/llm01-prompt-injection/

Text from web pages, emails, documents and tool results can contain instructions. Keep it clearly delimited as data, never grant it authority, restrict what the model can do after reading untrusted content (no exfiltration-capable tools, no secrets in context), and validate model outputs before acting on them. No prompt wording fully prevents injection; limit the blast radius.

## output-handling-security: Never execute or render model output without validation
tags: llm, insecure output handling, xss, sql injection, code execution, sanitization, security
keywords: rendered markdown from model, eval model output
refs: https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/

Model output is untrusted input to the next system. Escape it before rendering as HTML, never pass it to `eval`, shells or raw SQL, run generated code only in a sandbox with no secrets, and sanitize markdown links and images (they can exfiltrate data through URLs).

## llm-evaluation-suite: Build an evaluation set before changing prompts or models
tags: llm, evaluation, evals, regression testing, golden dataset, llm as judge, metrics
keywords: did the new prompt make it worse
refs: https://docs.claude.com/en/docs/test-and-evaluate/develop-tests

Collect representative and adversarial cases with expected properties, score them automatically (exact checks, code execution, or an LLM judge calibrated against human labels), and run the suite on every prompt, model or retrieval change. Track cost and latency alongside quality, and repeat runs where outputs are nondeterministic.

## llm-judge-calibration: Calibrate LLM-as-judge against human labels
tags: llm, llm as judge, evaluation, rubric, bias, agreement, grading
keywords: judge always says pass
refs: https://docs.claude.com/en/docs/test-and-evaluate/develop-tests#grading-evals

LLM judges are biased toward longer answers, their own outputs and the first option shown. Give the judge a specific rubric and reference answer, ask for a reason before the verdict, randomize option order for pairwise comparisons, and measure agreement with human labels on a sample before trusting the scores. Prefer deterministic checks where possible.

## token-budgeting: Budget context: send only what the task needs
tags: llm, tokens, context window, token optimization, cost, latency, truncation
keywords: huge prompts, cost too high
refs: https://docs.claude.com/en/docs/build-with-claude/context-windows

Every input token costs money and latency and can dilute attention. Retrieve the few relevant passages instead of whole documents, summarize or drop stale conversation turns, remove boilerplate from tool results, set `max_tokens` to what the output needs, and count tokens with the provider's tokenizer/counting API rather than estimating by characters when budgets are tight.

## prompt-caching: Cache stable prompt prefixes
tags: llm, prompt caching, cost reduction, latency, system prompt, cache breakpoints
keywords: same long system prompt every request
refs: https://docs.claude.com/en/docs/build-with-claude/prompt-caching

Put stable content (system prompt, tool definitions, reference documents) first and variable content last, and mark the stable prefix for caching where the provider supports it. Cached reads cost a fraction of normal input tokens; any change early in the prefix invalidates everything after it, so do not put timestamps or request IDs at the top.

## model-routing-cost: Route requests to the smallest model that meets the quality bar
tags: llm, model selection, cost optimization, routing, latency, batch api
keywords: using largest model for everything
refs: https://docs.claude.com/en/docs/about-claude/models/choosing-a-model

Measure quality per task on your eval set and use smaller, cheaper models where they pass (classification, extraction, routing), reserving larger models for hard reasoning. Use batch APIs for non-urgent bulk work (typically discounted) and stream responses for interactive latency.

## context-management-long-conversations: Manage long conversations explicitly
tags: llm, context management, conversation history, summarization, memory, context window
keywords: context window exceeded, model forgot earlier instructions
refs: https://docs.claude.com/en/docs/build-with-claude/context-windows

Do not append history forever. Keep the system prompt and the most recent turns, summarize or drop older ones, store durable facts in an external memory the application retrieves when relevant, and clear large tool outputs once they have been used. Re-state critical constraints rather than relying on a message from far back.

## retries-and-rate-limits-llm: Handle rate limits, overloads and timeouts from model APIs
tags: llm, rate limits, 429, retries, backoff, streaming, timeouts, resilience
keywords: 529 overloaded, requests fail at peak
refs: https://docs.claude.com/en/api/errors

Model APIs return 429 (rate limited) and overload/5xx errors under load. Retry with exponential backoff and jitter honoring `retry-after`, set client timeouts suited to long generations (or stream), cap concurrency below your rate limits, and degrade gracefully (queue, smaller model, cached answer) instead of failing the user request.

## hallucination-grounding: Ground answers in sources and let the model say it does not know
tags: llm, hallucination, grounding, citations, factuality, rag, uncertainty
keywords: model invented facts, fake citations
refs: https://docs.claude.com/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations

Instruct the model to answer only from provided sources, to quote or cite the passages it used, and to say when the sources do not contain the answer. Verify citations programmatically (the quoted text must exist in the source) and evaluate the unanswerable cases explicitly.

## secrets-and-pii-in-prompts: Keep secrets out of prompts and minimize personal data
tags: llm, secrets, pii, privacy, data minimization, logging, security, redaction
keywords: api key in system prompt, logs contain prompts with pii
refs: https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/

Anything in a prompt can appear in output. Never put credentials or internal secrets in prompts; give tools scoped credentials outside the model's view. Send only the personal data the task needs, redact it from logs and traces, and check your provider's data-retention settings for the data class.

## fine-tuning-when: Fine-tune only after prompting and retrieval are exhausted, and evaluate it
tags: llm, fine tuning, lora, training data, evaluation, overfitting, model customization
keywords: should we fine tune
refs: https://platform.openai.com/docs/guides/fine-tuning#when-to-use-fine-tuning

Fine-tuning teaches format, style and narrow behaviors; it is a poor way to add frequently changing knowledge (use retrieval). Try prompting, examples and RAG first; when fine-tuning, use clean, deduplicated, representative examples, hold out an evaluation split, and compare against the prompted baseline on the same eval set.

## inference-serving: Serve self-hosted models with batching, quantization and limits
tags: llm, inference, model serving, vllm, batching, quantization, gpu, latency, throughput
keywords: gpu underutilized, slow self hosted model
refs: https://docs.vllm.ai/en/latest/

Use a serving engine with continuous batching and paged KV caching (vLLM, TGI, TensorRT-LLM) rather than a naive per-request loop, consider weight quantization when memory-bound (and measure the quality impact), cap input and output lengths per request, and track time-to-first-token and tokens/second at your target concurrency.
