FROM docker.parapy.nl/parapy-cloud-app:3.11 as parent

ARG PARAPY_PYPI_USERNAME_TARGET=/run/secrets/PARAPY_PYPI_USERNAME
ARG PARAPY_PYPI_PASSWORD_TARGET=/run/secrets/PARAPY_PYPI_PASSWORD

COPY --chown=$PP_UID:$PP_GID requirements.txt requirements.txt

RUN --mount=type=secret,id=PARAPY_PYPI_USERNAME,uid=$PP_UID,target=${PARAPY_PYPI_USERNAME_TARGET} \
    --mount=type=secret,id=PARAPY_PYPI_PASSWORD,uid=$PP_UID,target=${PARAPY_PYPI_PASSWORD_TARGET} \
    PARAPY_PYPI_USERNAME=$(cat ${PARAPY_PYPI_USERNAME_TARGET}) && \
    export PARAPY_PYPI_USERNAME && \
    PARAPY_PYPI_PASSWORD=$(cat ${PARAPY_PYPI_PASSWORD_TARGET}) && \
    export PARAPY_PYPI_PASSWORD && \
    python3 -m pip install -r requirements.txt \
    --no-cache-dir \
    --no-input \
    --index-url https://${PARAPY_PYPI_USERNAME}:${PARAPY_PYPI_PASSWORD}@pypi.parapy.nl/simple/ && \
    rm -f requirements.txt

WORKDIR /app
EXPOSE 8000

COPY --chown=$PP_UID:$PP_GID src src
COPY --chown=$PP_UID:$PP_GID main.py main.py

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--loop", "asyncio"]
