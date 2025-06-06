FROM intelanalytics/ipex-llm-serving-cpu:latest

WORKDIR /llm

ENV PORT=8000
ENV MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
ENV MODEL_PATH=/llm/models/meta-llama/Llama-3.1-8B-Instruct
ENV QUANTIZATION=sym_int4
ENV MAX_MODEL_LEN=4096
ENV MAX_NUM_BATCHED_TOKENS=10240
ENV MAX_NUM_SEQS=12
ENV TENSOR_PARALLEL_SIZE=1

COPY start_server.sh start_server.sh
