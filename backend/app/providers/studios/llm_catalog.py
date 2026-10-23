"""Provider/model suggestions verified against official docs on 2026-10-12.

Suggestions do not assert account access or a successful live qualification.
Any model ID may be registered against an explicitly configured endpoint.
"""


def preset(identifier, label, protocol, url, models, source, **extra):
    return {
        "id": identifier, "label": label, "protocol": protocol, "baseUrl": url,
        "models": [{"id": model, "label": name} for model, name in models],
        "documentationUrl": source, "verifiedAt": "2026-10-12",
        "qualification": "documentation_verified_live_access_pending", **extra,
    }


PROVIDERS = [
    preset("openai", "OpenAI", "openai_responses", "https://api.openai.com/v1", [
        ("gpt-6.1-sol", "GPT-6.1 Sol"), ("gpt-6-astra", "GPT-6 Astra"), ("gpt-6-luna", "GPT-6 Luna"),
    ], "https://developers.openai.com/api/docs/models"),
    preset("anthropic", "Anthropic", "anthropic_messages", "https://api.anthropic.com/v1", [
        ("claude-sonnet-5-5", "Claude Sonnet 5.5"), ("claude-opus-5-5", "Claude Opus 5.5"),
        ("claude-haiku-5-5", "Claude Haiku 5.5"), ("claude-fable-5-1", "Claude Fable 5.1"),
    ], "https://platform.claude.com/docs/en/models/overview", authHeader="x-api-key", authPrefix=""),
    preset("google", "Google Gemini", "gemini_generate", "https://generativelanguage.googleapis.com/v1beta", [
        ("gemini-3.8-flash", "Gemini 3.8 Flash"), ("gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite"),
    ], "https://ai.google.dev/gemini-api/docs/models", authHeader="x-goog-api-key", authPrefix=""),
    preset("mistral", "Mistral", "openai_chat", "https://api.mistral.ai/v1", [
        ("mistral-large-4", "Mistral Large 4 · prévia"), ("mistral-small-2603", "Mistral Small 4"),
    ], "https://docs.mistral.ai/models"),
    preset("deepseek", "DeepSeek", "openai_chat", "https://api.deepseek.com", [
        ("deepseek-flash", "DeepSeek Flash"), ("deepseek-v4-pro", "DeepSeek V4 Pro"),
    ], "https://api-docs.deepseek.com/"),
    preset("xai", "xAI", "openai_responses", "https://api.x.ai/v1", [
        ("grok-4.7", "Grok 4.7"),
    ], "https://docs.x.ai/developers/models"),
    preset("cohere", "Cohere", "cohere_chat", "https://api.cohere.com/v2", [
        ("command-a-plus-05-2026", "Command A+"), ("command-a-reasoning-08-2025", "Command A Reasoning"),
    ], "https://docs.cohere.com/docs/models"),
    preset("groq", "Groq", "openai_chat", "https://api.groq.com/openai/v1", [
        ("openai/gpt-oss-120b", "GPT-OSS 120B"), ("openai/gpt-oss-20b", "GPT-OSS 20B"),
        ("qwen/qwen3.8-27b", "Qwen3.8 27B"),
    ], "https://console.groq.com/docs/models"),
    preset("together", "Together AI", "openai_chat", "https://api.together.xyz/v1", [
        ("Qwen/Qwen3.8-2.4T-A95B", "Qwen3.8"), ("moonshotai/Kimi-K3", "Kimi K3"),
    ], "https://docs.together.ai/docs/serverless/models"),
    preset("fireworks", "Fireworks AI", "openai_chat", "https://api.fireworks.ai/inference/v1", [
        ("accounts/fireworks/models/kimi-k3", "Kimi K3"),
        ("accounts/fireworks/models/glm-5p3-flash", "GLM 5.3 Flash"),
    ], "https://docs.fireworks.ai/getting-started/quickstart"),
    preset("openrouter", "OpenRouter", "openai_chat", "https://openrouter.ai/api/v1", [
        ("anthropic/claude-opus-5.5", "Claude Opus 5.5 · OpenRouter"),
    ], "https://openrouter.ai/anthropic/claude-opus-5.5", verifiedAt="2026-10-21"),
    preset("ollama", "Ollama · local", "ollama_chat", "http://127.0.0.1:11434", [
        ("qwen3:8b", "Qwen3 8B · local"), ("gpt-oss:20b", "GPT-OSS 20B · local"),
    ], "https://docs.ollama.com/api/openai-compatibility", authPrefix="", billingMode="local_free"),
    preset("custom", "Endpoint personalizado", "openai_chat", "", [],
           "", qualification="endpoint_configuration_required"),
]
