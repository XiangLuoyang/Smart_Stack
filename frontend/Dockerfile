# Smart Stack 前端镜像:多阶段构建
#   Stage 1 (build): Node + Vite 编译静态资源到 dist/
#   Stage 2 (serve): nginx 托管 dist/,并通过反向代理把 /api 转给后端容器

# ---------- Stage 1: build ----------
FROM node:20-alpine AS build
WORKDIR /app

# npm 国内镜像(可选,网络好可删)
RUN npm config set registry https://registry.npmmirror.com

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: serve ----------
FROM nginx:1.27-alpine AS serve

# 替换默认配置:SPA 兜底 + /api 反代(含 SSE)
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
