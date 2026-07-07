# Taskly — Flask Todo List Application

A full-featured todo list app with a modern UI, built with Flask + SQLite, fully dockerized, and ready to deploy on Kubernetes.

## Features

- ✅ Add tasks with **title, description, and priority** (low/medium/high)
- ✏️ Edit any task in place via a modal
- 🗑️ Delete individual tasks
- ☑️ Mark as completed / unmark (toggle)
- 🔍 Search tasks by title/description
- 🧹 Filter by All / Active / Completed, and bulk "Clear completed"
- 📊 Live stats bar (total, active, completed)
- 💅 Polished, responsive UI with animations, no external UI framework
- 🩺 `/healthz` and `/readyz` endpoints for Kubernetes probes
- 🔒 Runs as a non-root user in Docker

## Project Structure

```
todoapp/
├── app.py                 # Flask app + REST API + SQLite persistence
├── requirements.txt
├── Dockerfile              # Multi-stage, non-root, gunicorn
├── docker-compose.yml       # For quick local testing
├── .dockerignore
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/script.js
└── k8s/
    ├── 00-namespace.yaml
    ├── 01-configmap.yaml
    ├── 02-pvc.yaml
    ├── 03-deployment.yaml
    ├── 04-service.yaml
    ├── 05-ingress.yaml
    └── kustomization.yaml
```

## API Endpoints

| Method | Endpoint                       | Description                      |
|--------|---------------------------------|-----------------------------------|
| GET    | `/api/todos?status=&search=`    | List todos (with filter/search)   |
| GET    | `/api/todos/<id>`                | Get single todo                   |
| POST   | `/api/todos`                     | Create todo `{title, description, priority}` |
| PUT    | `/api/todos/<id>`                 | Update todo                       |
| PATCH  | `/api/todos/<id>/toggle`          | Toggle completed state            |
| DELETE | `/api/todos/<id>`                 | Delete a todo                     |
| DELETE | `/api/todos/clear-completed`      | Delete all completed todos        |
| GET    | `/healthz`                        | Liveness check                    |
| GET    | `/readyz`                         | Readiness check (DB connectivity) |

## Run Locally (no Docker)

```bash
pip install -r requirements.txt
python app.py
# Visit http://localhost:5000
```

## Run with Docker

```bash
docker build -t todo-app:latest .
docker run -d -p 5000:5000 -v todo-data:/app/data --name todo-app todo-app:latest
# Visit http://localhost:5000
```

Or with Docker Compose:

```bash
docker compose up --build
```

## Deploy to Kubernetes

The manifests live in `k8s/`. They create a dedicated `todo-app` namespace, config, persistent storage, deployment, service, and ingress.

1. **Build and push the image** to a registry your cluster can pull from:

   ```bash
   docker build -t <your-registry>/todo-app:latest .
   docker push <your-registry>/todo-app:latest
   ```

   Then update `image:` in `k8s/03-deployment.yaml` to `<your-registry>/todo-app:latest`.
   (If using a local cluster like `kind` or `minikube`, load the image instead:
   `kind load docker-image todo-app:latest` or `minikube image load todo-app:latest`.)

2. **Apply the manifests** (either approach works):

   ```bash
   # Using kustomize (recommended)
   kubectl apply -k k8s/

   # OR apply files individually in order
   kubectl apply -f k8s/00-namespace.yaml
   kubectl apply -f k8s/01-configmap.yaml
   kubectl apply -f k8s/02-pvc.yaml
   kubectl apply -f k8s/03-deployment.yaml
   kubectl apply -f k8s/04-service.yaml
   kubectl apply -f k8s/05-ingress.yaml
   ```

3. **Verify:**

   ```bash
   kubectl -n todo-app get pods,svc,ingress,pvc
   ```

4. **Access the app:**
   - Via Ingress: add `todo-app.local` to your `/etc/hosts` pointing at the ingress controller's external IP, then browse to `http://todo-app.local` (requires an nginx ingress controller installed in the cluster).
   - Or port-forward for quick testing:
     ```bash
     kubectl -n todo-app port-forward svc/todo-app-service 8080:80
     # Visit http://localhost:8080
     ```

### Notes on scaling

This app uses SQLite on a `ReadWriteOnce` PersistentVolumeClaim, which only supports a single writer safely. The Deployment is therefore pinned to **`replicas: 1`** with a `Recreate` update strategy. To scale horizontally, swap SQLite for a networked database (e.g., PostgreSQL) and remove the PVC/replica constraint.

## Tech Stack

- **Backend:** Flask 3, SQLite
- **Server:** Gunicorn (production WSGI server)
- **Frontend:** Vanilla HTML/CSS/JS (no build step required)
- **Container:** Multi-stage Docker build, non-root user, healthchecks
- **Orchestration:** Kubernetes (Namespace, ConfigMap, PVC, Deployment, Service, Ingress)
