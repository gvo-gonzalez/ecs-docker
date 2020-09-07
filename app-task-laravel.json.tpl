[
       {
            "name": "${PHP_CONTAINER_NAME}",
            "image": "${PHP_REPOSITORY_URL}:nginx-svc-${PHP_APP_VERSION}",
            "memory": 256,
            "cpu": 256,
            "essential": true,
            "portMappings": [
                {
                    "containerPort": 80,
                    "hostPort": 80,
                    "protocol": "tcp"
                }
            ],
            "links": [
                "${PHP_FPM}"
            ]
       },
       {
            "name": "${PHP_FPM}",
            "image": "${PHP_REPOSITORY_URL}:${PHP_APP_VERSION}",
            "memory": 256,
            "cpu": 256,
            "essential": true,
            "workingDirectory": "${PHP_APP_WORK_DIR}"
        }
        
]

