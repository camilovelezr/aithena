# PostGres DB

This projects provide deployments for postgres using:
    - docker compose
    - helm charts

## Configure 

Copy and rename `.env-sample` to `.env` and update values according
to your configuration.

## Deploy 

```shell
helm dependency update
helm install ${RELEASE} . -n ${NAMESPACE}
```