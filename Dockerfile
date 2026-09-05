# Placeholder — replaced at venue from reference Dockerfile.
# Contract: judges run `docker build -t tieout .` then
# `docker run --rm -e <KEYS> -v <dataset>:/data:ro -v <empty>:/out tieout`
# Pipeline reads /data (dataset.json + init workbooks + prompt.txt), writes to /out:
# predictions.jsonl, outputs/<id>.xlsx, traces/<id>.jsonl, run.log
# Model-written code executes INSIDE this container only.
FROM python:3.11-slim
WORKDIR /app
COPY research/pyproject.toml research/uv.lock ./
# VENUE: install deps + libreoffice-calc for recalc scoring, copy harness/, set ENTRYPOINT
# ENTRYPOINT ["python", "harness/pipeline.py", "--dataset-dir", "/data", "--out-dir", "/out"]
