"""tieout adapters — pluggable complete(prompt) -> (text, in_tokens, out_tokens).

tinker is PRIMARY (Qwen3.8-27B sampling + fine-tune). gemini is a spare teacher
(Gemini 3.7 Flash baseline 68.3%). wandb routes to W&B Serverless Inference
(OpenAI-compatible; Weave auto-traces the SDK calls). No OpenRouter (unfunded).
Temperature 0.
"""

import asyncio
import os

from weave_hooks import traceable_call


def make_completer(spec: str, temperature: float = 0.0):
    """spec: 'gemini:<model>', 'tinker:<base>|<model_path>', or 'wandb:<model>'."""
    if spec.startswith("gemini:"):
        fn = _gemini(spec.split(":", 1)[1], temperature)
    elif spec.startswith("tinker:"):
        rest = spec.split(":", 1)[1]
        base, _, path = rest.partition("|")
        fn = _tinker(base, path or None, temperature)
    elif spec.startswith("wandb:"):
        fn = _wandb(spec.split(":", 1)[1], temperature)
    else:
        raise ValueError(f"unknown adapter spec: {spec}")
    return traceable_call(fn, name="model.complete")


def _gemini(model: str, temperature: float = 0.0):
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def complete_sync(prompt: str, system: str):
        r = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "systemInstruction": system,
                "temperature": temperature,
                "maxOutputTokens": 16384,
            },
        )
        in_tok = out_tok = None
        if r.usage_metadata:
            in_tok = r.usage_metadata.prompt_token_count
            out_tok = r.usage_metadata.candidates_token_count
        return r.text or "", in_tok, out_tok

    async def complete(prompt: str, system: str = ""):
        return await asyncio.to_thread(complete_sync, prompt, system)

    complete.model_name = f"gemini:{model}"
    complete.temperature = temperature
    return complete


def _tinker(base_model: str, model_path: str | None, temperature: float = 0.0):
    """Proven pattern: model's own chat template -> ModelInput -> sample -> decode.

    project_id selects the Tinker org project (TINKER_PROJECT_ID env). Thinking
    (<think>...</think>) in replies is handled by the lenient parser downstream.
    """
    import os

    import tinker
    from tinker import types
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    client = tinker.ServiceClient(
        project_id=os.environ.get("TINKER_PROJECT_ID") or None
    )
    sampler = client.create_sampling_client(
        base_model=base_model, model_path=model_path or None
    )
    tokenizer = get_tokenizer(base_model)

    def _encode(messages: list[dict]):
        # enable_thinking=False: Qwen3 thinking mode leaks CoT as plain text and
        # drowns the JSON; values-first wants direct answers (parser still lenient).
        try:
            enc = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                enable_thinking=False,
            )
        except TypeError:  # non-Qwen template without the kwarg
            enc = tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=True
            )
        tokens = enc["input_ids"] if hasattr(enc, "keys") else enc
        if hasattr(tokens, "tolist"):
            tokens = tokens.tolist()
        if tokens and isinstance(tokens[0], list):
            tokens = tokens[0]
        return tokens

    async def complete(prompt: str, system: str = ""):
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        in_tok = len(_encode(messages))
        resp = await sampler.sample_async(
            prompt=types.ModelInput.from_ints(_encode(messages)),
            num_samples=1,
            # Qwen docs: recommend 16k output headroom for complex tasks to avoid
            # silent truncation of long JSON answers.
            sampling_params=types.SamplingParams(
                max_tokens=16384, temperature=temperature
            ),
        )
        seq = resp.sequences[0]
        return tokenizer.decode(seq.tokens), in_tok, len(seq.tokens)

    complete.model_name = model_path or base_model
    complete.temperature = temperature
    return complete


def _wandb(model: str, temperature: float = 0.0):
    """W&B Serverless Inference — OpenAI-compatible chat completions.

    Endpoint: https://api.inference.wandb.ai/v1, key from WANDB_API_KEY.
    WANDB_INFERENCE_PROJECT (entity/project, optional) tags usage in W&B.
    Weave's OpenAI integration auto-traces these calls once weave.init ran.
    """
    import openai

    kwargs = {
        "base_url": "https://api.inference.wandb.ai/v1",
        "api_key": os.environ["WANDB_API_KEY"],
    }
    project = os.environ.get("WANDB_INFERENCE_PROJECT")
    if project:
        kwargs["project"] = project
    client = openai.AsyncOpenAI(**kwargs)
    model = model or "meta-llama/Llama-3.3-70B-Instruct"

    async def complete(prompt: str, system: str = ""):
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        r = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=16384,
            # Qwen thinking burns the whole budget in `reasoning` and leaves
            # `content` empty on truncation — same fix as the tinker adapter.
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        usage = r.usage
        msg = r.choices[0].message
        return (
            msg.content or getattr(msg, "reasoning", None) or "",
            getattr(usage, "prompt_tokens", None),
            getattr(usage, "completion_tokens", None),
        )

    complete.model_name = f"wandb:{model}"
    complete.temperature = temperature
    return complete
