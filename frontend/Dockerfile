# Stage 1: Build the Flutter Web app
# Flutter 3.19.6 (Dart 3.3.4) is required — web:0.3.0 (pulled by file_picker/fl_chart)
# uses JSObject as a class supertype which is only valid in Dart <=3.3.x
FROM ghcr.io/cirruslabs/flutter:3.19.6 AS build

WORKDIR /app

# Copy pubspec first for layer caching; use pub upgrade to resolve compatible versions
COPY pubspec.yaml ./
RUN flutter pub upgrade

# Copy source and build
COPY . .
ARG BACKEND_URL
RUN flutter build web --release --no-tree-shake-icons --dart-define=BACKEND_URL=$BACKEND_URL

# Stage 2: Serve with Nginx
FROM nginx:alpine

COPY --from=build /app/build/web /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
