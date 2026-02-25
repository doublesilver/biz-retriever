FROM nginx:alpine

# Copy all frontend files (source mode)
COPY . /usr/share/nginx/html

# Copy nginx main configuration (with DDoS protection)
COPY nginx.conf /etc/nginx/nginx.conf

# Copy server configuration
COPY nginx-static.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
