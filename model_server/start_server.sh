#!/bin/bash
python3 -m ipex_llm.vllm.cpu.entrypoints.openai.api_server \
    --served-model-name ${MODEL_NAME} \
    --port ${PORT} \
    --model ${MODEL_PATH} \
    --trust-remote-code \
    --device cpu \
    --dtype bfloat16 \
    --enforce-eager \
    --load-in-low-bit ${QUANTIZATION} \
    --max-model-len ${MAX_MODEL_LEN} \
    --max-num-batched-tokens ${MAX_NUM_BATCHED_TOKENS} \
    --max-num-seqs ${MAX_NUM_SEQS} \
    --tensor-parallel-size ${TENSOR_PARALLEL_SIZE}