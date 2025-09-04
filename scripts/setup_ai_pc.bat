
@REM Downlaod and unzip openvino modelserver
curl -L https://github.com/openvinotoolkit/model_server/releases/download/v2025.2.1/ovms_windows_python_off.zip -o ovms.zip
tar -xf ovms.zip

curl https://raw.githubusercontent.com/openvinotoolkit/model_server/refs/heads/releases/2025/2/demos/common/export_models/export_model.py -o export_model.py
pip3 install -r https://raw.githubusercontent.com/openvinotoolkit/model_server/refs/heads/releases/2025/2/demos/common/export_models/requirements.txt
mkdir models

python scripts/export_model.py text_generation --source_model Qwen/Qwen2.5-7B-Instruct --target_device NPU --config_file_path models/config.json --ov_cache_dir models/.ov_cache --model_repository_path models  --overwrite_models --max_prompt_len 1024
