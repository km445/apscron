# APSCRON
APSCRON - Async task manager built with APScheduler and aiohttp. Operates as JSON API but can also render vue front-end if needed.

## Application demo instructions

Note: you take it upon yourself to install docker and docker-compose, which are installed separately; use these links as a guide:
1. https://docs.docker.com/engine/install/ubuntu/
1. https://docs.docker.com/compose/install/

1. Clone the project `git clone https://github.com/km445/apscron.git`.
1. Go to project root and run `docker-compose up --build`.
1. Go to `localhost:8080/front/login` in your browser to use web interface (with username "admin" and password "1").
