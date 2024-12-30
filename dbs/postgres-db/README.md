# PostGres DB

This projects provide deployments for postgres using:
    - docker compose
    - helm charts

## Configure 

Copy and rename `.env-sample` to `.env` and update values according
to your configuration.

Create a secret from this `.env` file

```shell
kubectl create secret generic aithenadb-secret --from-env-file=.env -n namespace
```

## Deploy 

### Regular Deployment

```shell
helm dependency update
helm install ${RELEASE} . -n ${NAMESPACE}
```

### Large Scale Deployment

Rename `custom-depl-sample.yaml` to `custom-depl.yaml`

Update config and deply :

```shell
kubectl apply -f custom-depl.yaml
```

## Admin

```
docker pull dpage/pgadmin4
```

```
docker run -p 30980:80 \
    -e 'PGADMIN_DEFAULT_EMAIL=${ADMIN_EMAIL}' \
    -e 'PGADMIN_DEFAULT_PASSWORD=${ADMIN_PASSWORD}' \
    -d dpage/pgadmin4 
```
