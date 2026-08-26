FROM nginx:alpine

# 复制 Nginx 站点配置（前端 dist 目录通过 docker-compose 挂载）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
