# Milestone 6: Provider Layer

## Purpose

Define cassiopeia's provider boundary for chat models, tool-calling capable
models, structured-output capable models, and embeddings. This milestone gives
later runtime work a stable way to ask for model and embedding capabilities
without importing vendor SDKs or scattering provider-specific assumptions across
personas, workflows, memory, tools, or gateways.

The provider layer should be thin. Pydantic AI should handle the model-provider
adaptation where it fits, while cassiopeia owns capability metadata, configured
profiles, embedding interfaces, error shapes, and tests that prove the boundary
works for OpenAI and Ollama.

## Scope

### In Scope

- Provider package layout under `src/cassiopeia/providers/`.
- Provider profile and capability models for chat, tool calling, structured
  output, and embeddings.
- Interfaces/protocols for chat model access and embedding providers.
- OpenAI and Ollama provider adapters through the existing stack, using
  Pydantic AI where appropriate.
- Embedding provider abstraction with `embed_text`, `embed_batch`, provider id,
  model id, and vector dimension.
- Configuration models or config references needed to select provider/model
  profiles without storing raw secrets.
- Capability checks that fail clearly when a selected model cannot support a
  requested feature.
- Provider error types for missing configuration, unsupported capabilities,
  provider failures, invalid structured output, and embedding dimension
  mismatches.
- Focused tests with fake providers and any practical adapter smoke tests that
  do not require live network credentials.

### Out of Scope

- Agent runtime orchestration, conversation memory construction, tool execution,
  or workflow execution.
- Gateway-specific provider behaviour or prompt rendering.
- CLI management commands for providers beyond small validation helpers if
  needed.
- Adding new provider dependencies unless the existing stack cannot support a
  required 1.0 provider path.
- Live API integration tests that require real OpenAI or Ollama availability in
  default verification.
- Provider routers such as OpenRouter unless explicitly promoted into the
  required 1.0 scope later.
- Secret storage beyond referencing environment variable names and using the
  existing settings pattern.

## Deliverables

- `src/cassiopeia/providers/` package with provider-facing models, ports,
  errors, and adapter modules, likely:

  ```text
  providers/
    __init__.py
    models.py
    ports.py
    errors.py
    registry.py
    openai.py
    ollama.py
    embeddings.py
  ```

- Capability metadata models for chat, tool calling, structured output, and
  embeddings.
- Provider profile models that can be referenced by personas, workspaces, and
  global config without raw secrets.
- Chat/model provider protocol suitable for the later runtime milestone.
- Embedding provider protocol suitable for memory indexing and reindexing.
- OpenAI and Ollama adapters using existing dependencies.
- Fake providers for tests so default verification does not require network or
  credentials.
- Tests under `tests/providers/` for profile validation, capability checks,
  adapter selection, embedding dimension validation, fake chat/structured-output
  calls, fake embedding calls, and import boundaries.
- Documentation updates if the provider boundary changes scope or package
  ownership.

## Tasks

- [ ] Review `docs/cassiopeia-1.0-scope.md` and
      `docs/project-structure.md` before editing provider code.
- [ ] Create the `cassiopeia.providers` package layout with model, port, error,
      registry, OpenAI, Ollama, and embedding modules.
- [ ] Define provider identity, model profile, embedding profile, and capability
      metadata models.
- [ ] Define chat/model provider protocols for plain chat, tool calling, and
      structured output requests.
- [ ] Define embedding provider protocols with text, batch, vector dimension,
      provider id, and model id.
- [ ] Define provider errors for missing configuration, unsupported
      capabilities, provider failures, invalid structured output, and embedding
      dimension mismatches.
- [ ] Add configuration shapes or references for selecting OpenAI, Ollama, and
      embedding profiles without storing raw API keys in JSON files.
- [ ] Implement a small provider registry that resolves configured provider ids
      to provider adapters or test fakes.
- [ ] Implement OpenAI adapter wiring through the existing Pydantic AI stack
      where practical.
- [ ] Implement Ollama adapter wiring through the existing Pydantic AI stack
      where practical.
- [ ] Implement embedding adapters or adapter seams for OpenAI and Ollama
      embeddings, keeping embeddings separate from chat providers.
- [ ] Add fake chat and embedding providers for deterministic tests.
- [ ] Add tests for capability checks, including unsupported tool calling and
      unsupported structured output.
- [ ] Add tests that embedding vectors match the configured vector dimension and
      that mismatches fail clearly.
- [ ] Add tests that default verification does not require network access,
      local Ollama, or live OpenAI credentials.
- [ ] Add tests that runtime, memory, workflow, and persona code can depend on
      provider ports/models without importing provider implementation details.
- [ ] Update milestone 6 decisions and open questions as provider boundaries are
      settled.

## Acceptance Criteria

- [ ] Later runtime code has a stable provider-facing API for chat, tool
      calling, structured output, and embeddings.
- [ ] OpenAI and Ollama provider profiles can be represented without raw
      secrets in user-authored JSON files.
- [ ] Capability checks can reject unsupported chat, tool-calling,
      structured-output, or embedding requests before runtime code proceeds.
- [ ] Embedding providers expose provider id, model id, vector dimension,
      single-text embedding, and batch embedding.
- [ ] Embedding results validate vector dimension before memory storage uses
      them.
- [ ] Provider-specific SDK or Pydantic AI integration details stay inside
      `cassiopeia.providers`.
- [ ] Default tests use fakes or local-only checks and do not require live
      network credentials.
- [ ] OpenAI and Ollama adapter seams are present even if live smoke tests are
      optional and skipped by default.
- [ ] Full agent runtime, memory retrieval, tool execution, workflow execution,
      and gateway behaviour remains deferred to later milestones.
- [ ] `scripts/verify` passes, or any failure is documented with the remaining
      risk.

## Verification

```sh
scripts/verify
```

Optional focused checks during implementation:

```sh
uv run pytest tests/providers
```

Optional live smoke checks may be added only if they are explicitly skipped by
default unless the required environment variables or local services are present.

## Decisions

- OpenAI and Ollama are the required 1.0 providers.
- Embeddings are a separate provider abstraction from chat/model calls.
- Pydantic AI should be used for model-provider adaptation where it fits, but
  runtime code should depend on cassiopeia provider ports rather than vendor or
  Pydantic AI details directly.
- Provider configuration should reference environment variable names for secrets
  instead of storing raw tokens in JSON config.
- Default verification should not require network access, OpenAI credentials, or
  a running local Ollama service.
- Provider routers such as OpenRouter remain stretch work unless explicitly
  promoted later.

## Open Questions

- Exact typed request and response shapes the runtime will need for tool calls
  and structured output.
- Whether provider capability metadata should be user-authored, discovered, or a
  small built-in catalogue for 1.0.
- How much Ollama model capability detection can be done reliably without live
  network/service checks.
- Whether embedding batch limits and retry policy belong in providers or later
  runtime/memory services.

## Notes

This milestone should make the provider layer callable and testable without
building the agent runtime. Keep prompts, context assembly, tool execution,
workflow node execution, and memory retrieval policy in later milestones. The
provider layer owns adapter boundaries, capability checks, configured profiles,
and embedding calls.
