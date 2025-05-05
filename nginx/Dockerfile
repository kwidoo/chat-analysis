FROM nginx:latest

RUN apt-get update && apt-get install -y gettext-base

# Copy nginx configuration template
COPY default.conf /etc/nginx/templates/default.conf.template

# Expose port 80
EXPOSE 80

# Use environment variables and start nginx
CMD ["/bin/sh", "-c", "envsubst '$SERVER_NAME' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
