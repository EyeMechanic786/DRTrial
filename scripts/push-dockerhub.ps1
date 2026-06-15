# Push DRTrial images to Docker Hub
# Prerequisite: docker login -u eyemechanic786

$ErrorActionPreference = "Stop"
$User = "eyemechanic786"
$Tag = if ($args[0]) { $args[0] } else { "latest" }

Write-Host "Tagging images for Docker Hub ($User)..."
docker tag drtrial-api:latest "${User}/drtrial-api:${Tag}"
docker tag drtrial-web:latest "${User}/drtrial-web:${Tag}"
docker tag drtrial-worker:latest "${User}/drtrial-worker:${Tag}"

Write-Host "Pushing API..."
docker push "${User}/drtrial-api:${Tag}"
Write-Host "Pushing Web..."
docker push "${User}/drtrial-web:${Tag}"
Write-Host "Pushing Worker..."
docker push "${User}/drtrial-worker:${Tag}"

Write-Host ""
Write-Host "Published:"
Write-Host "  https://hub.docker.com/r/${User}/drtrial-api"
Write-Host "  https://hub.docker.com/r/${User}/drtrial-web"
Write-Host "  https://hub.docker.com/r/${User}/drtrial-worker"
