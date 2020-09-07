This script is intended to build and push your images to AWS ECR repository by building this frameworks:
- Laravel
- NodeJS
- ReactJS
- Nginx as sidecar proxy for each framework if required

This project includes a task definition for laravel as an example to upload and configure your ECS cluster replacing variables as required.

Running modes

1. Configure docker-stack.json file with your project information

2. 1 -  Build images locally only wihtout pushing up
        - python3 ecs-builder.py docker-stack.json local

2. 2 -  Build an push image to amazon ECR, this require aws cli to be installed and configured.
        - python3 ecs-builder.py docker-stack.json

Requirements:

- docker package
- awscli

python3 library:
- docker-py,
- gitpython,
- docker,
- nose,
- tornado,
- boto,
- boto3
