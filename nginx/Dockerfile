FROM nginx:stable-alpine

RUN mkdir -p /var/www/public

COPY src-code/phpapp/public /var/www/public

COPY nginx/single-proj.conf /etc/nginx/conf.d/default.conf
