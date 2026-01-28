FROM nginx:alpine

# Copy all frontend files (source mode)
COPY . /usr/share/nginx/html

# Copy nginx configuration
COPY nginx-static.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
