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
    import tinker
    from tinker import types

    sampler = tinker.ServiceClient().create_sampling_client(
        base_model=base_model, model_path=model_path
    )

    async def complete(prompt: str, system: str = ""):
        from tinker_cookbook import renderers
        from tinker_cookbook.model_info import get_recommended_renderer_name
        from tinker_cookbook.tokenizer_utils import get_tokenizer

        renderer = renderers.get_renderer(
            get_recommended_renderer_name(base_model), get_tokenizer(base_model)
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        model_input = renderer.build_generation_prompt(messages)
        params = types.SamplingParams(
            max_tokens=8192, temperature=0, stop=renderer.get_stop_sequences()
        )
        response = await sampler.sample_async(
            prompt=model_input, num_samples=1, sampling_params=params
        )
        tokens = response.sequences[0].tokens
        content = renderer.parse_response(tokens)[0]["content"]
        if not isinstance(content, str):
            content = "".join(
                p.get("text", "") for p in content if p.get("type") == "text"
            )
        return content, model_input.length, len(tokens)

    complete.model_name = model_path or base_model
    return complete
