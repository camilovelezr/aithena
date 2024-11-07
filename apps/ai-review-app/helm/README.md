## ai-review app

### Configure 

Rename `.vars-sample` to `.vars` and `source .vars`
Rename `.values-sample` to `.values` and update with: 

```shell
echo $OLLAMA_HOST
```

### Install

```shell
mh install ${RELEASE_NAME} . -n ${NAMESPACE}
``` 

## Test 

Create a tunnel to your host

```shell
ssh -L ${NODE_PORT}:127.0.0.1:${NODE_PORT} ${USER}@{REMOTE_HOST}
```

Browse to `http://localhost:${NODE_PORT}/dashboard`

