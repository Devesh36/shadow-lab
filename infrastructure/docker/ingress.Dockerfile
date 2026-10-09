FROM nginxinc/nginx-unprivileged:stable-alpine
COPY --chown=101:101 infrastructure/docker/nginx.conf /etc/nginx/nginx.conf
