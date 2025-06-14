set -e
echo "Building dockers..."
sudo docker-compose -f docker-compose-vllm.yml build
echo "dockers built."
echo "Starting dockers..."
sudo docker-compose -f docker-compose-vllm.yml up -d
echo "Done. Services up."
echo "START LOGS (backend)..."
docker logs -f shashguru-backend-1
