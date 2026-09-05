"""tieout adapters — pluggable complete(prompt) -> (text, in_tokens, out_tokens).

gemini is PRIMARY (free AI Studio key, strongest baseline). tinker serves the
fine-tuned checkpoint. No OpenRouter (unfunded). Temperature 0 everywhere.
"""

import asyncio
import os


def make_completer(spec: str):
    """spec: 'gemini:<model>' (e.g. gemini:gemini-3.7-flash) or 'tinker:<base>|<model_path>'."""
    if spec.startswith("gemini:"):
        return _gemini(spec.split(":", 1)[1])
    if spec.startswith("tinker:"):
        rest = spec.split(":", 1)[1]
        base, _, path = rest.partition("|")
        return _tinker(base, path or None)
    raise ValueError(f"unknown adapter spec: {spec}")


def _gemini(model: str):
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def complete_sync(prompt: str, system: str):
        r = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"systemInstruction": system, "temperature": 0},
        )
        in_tok = out_tok = None
        if r.usage_metadata:
            in_tok = r.usage_metadata.prompt_token_count
            out_tok = r.usage_metadata.candidates_token_count
        return r.text or "", in_tok, out_tok

    async def complete(prompt: str, system: str = ""):
        return await asyncio.get_event_loop().run_in_executor(
            None, complete_sync, prompt, system
        )

    complete.model_name = f"gemini:{model}"
    return complete


def _tinker(base_model: str, model_path: str | None):
    """Proven pattern: model's own chat template -> ModelInput -> sample -> decode.

    project_id selects the Tinker org project (TINKER_PROJECT_ID env). Thinking
    (<think>...</think>) in replies is handled by the lenient parser downstream.
    """
    import os

    import tinker
    from tinker import types
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    client = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    sampler = client.create_sampling_client(
        base_model=base_model, model_path=model_path or None
    )
    tokenizer = get_tokenizer(base_model)

    def _encode(messages: list[dict]):
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
            sampling_params=types.SamplingParams(max_tokens=8192, temperature=0),
        )
        seq = resp.sequences[0]
        return tokenizer.decode(seq.tokens), in_tok, len(seq.tokens)

    complete.model_name = model_path or base_model
    return complete
