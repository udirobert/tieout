# Ship container — research track. Judges run:
#   docker build -t tieout .
#   docker run --rm -e <KEYS via env> -v <dataset>:/data:ro -v <empty>:/out tieout
# Contract: /out gets predictions.jsonl, outputs/<id>.xlsx, traces/<id>.jsonl, run.log.
# Missing file or line = 0. Default --path hybrid = ship config (cell values /
# sheet codegen, recalc-gate fallback to values when soffice present).
FROM python:3.11-slim

# libreoffice-calc: recalc-as-gate (fatal formula errors → values-first fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        "openpyxl>=3.1" \
        "tinker>=0.27.1" \
        "tinker-cookbook>=0.5.7"

WORKDIR /app
COPY harness/ ./harness/
COPY research/sb.py ./research/sb.py
COPY skills/ ./skills/

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "harness/clone_run.py", "--dataset-dir", "/data", "--out-dir", "/out"]

