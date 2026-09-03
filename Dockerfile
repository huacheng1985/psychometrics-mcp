FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      r-base r-cran-erm r-cran-jsonlite r-cran-lavaan r-cran-psych r-cran-gparotation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY scripts/install_ordinal_invariance_dependencies.R /app/scripts/
RUN Rscript /app/scripts/install_ordinal_invariance_dependencies.R /opt/psychometrics-r
ENV PSYCHOMETRICS_R_LIBRARY=/opt/psychometrics-r
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY scripts/check_ordinal_invariance_mcp.py /app/scripts/
RUN python -m pip install .

RUN useradd --create-home --uid 10001 mcp
USER mcp

ENTRYPOINT ["psychometrics-mcp"]
