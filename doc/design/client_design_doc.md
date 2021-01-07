# SQLFlow Client Design Doc

## Overview

SQLFlow Client connects [sqlflowserver](https://github.com/sql-machine-learning/sqlflowserver).
It only one method `Run` which takes a SQL statement and returns a `RowSet` object.

## Example

```python
import sqlflow

client = sqlflow.Client(server_url='localhost:50051')

# Query SQL
rowset = client.run('SELECT ... FROM ...')
for row in rowset:
    print(row) # [1, 1]

# Execution SQL, prints
# Query OK, ... row affected (... sec)
client.run('DELETE FROM ... WHERE ...')

# ML SQL, prints
# epoch = 0, loss = ...
# epoch = 1, loss = ...
# ...
client.run('SELECT ... TRAIN ...')
```

## Service Protocol

`sqlflow.Client` uses grpc to contact the `sqlflowserver`. The service protocol
is defined [here](/proto/sqlfow/proto/sqlflow.proto)

## Implementaion

`sqlflow.Client.__init__` establishes a grpc stub/channel based on `server_url`.

`sqlflow.Client.run` takes a sql statement and returns a `RowSet` object.
```python
class Client:
    def __init__(self, host):
        channel = grpc.insecure_channel(host)
        self._stub = sqlflow_pb2_grpc.SQLFlowStub(channel)

    def _decode_protobuf(self, proto):
        '''decode rowset'''

    def run(self, operation):
        def rowset_gen():
            for res in self._stub.Run(sqlflow_pb2.Request(sql=operation)):
                if res.is_message():
                    log(res)
                else:
                    yield self._decode_protobuf(res)

        return RowSet(rowset_gen=rowset_gen)

class RowSet:
    def __init__(self, rowset_gen):
        res = [r for r in rowset_gen]
        if res:
            self._head = res[0]
            self._rows = res[1:]
        else:
            self._head, self._rows = None, None

    def __repr__(self):
        '''used for IPython: pretty prints self'''

    def rows(self):
        return self._rows

    def to_dataframe(self):
        '''convert to dataframes'''
```

## Pagination

Currently sqlflow server doesn't support pagination, neither does the client.
If we want to support it in the future, it can be implemented through passing
pageTokens. For example, the following code snippet from
[google-api-go-client](https://github.com/googleapis/google-api-go-client/blob/master/iterator/iterator.go#L68)

```go
// Function that fetches a page from the underlying service. It should pass
// the pageSize and pageToken arguments to the service, fill the buffer
// with the results from the call, and return the next-page token returned
// by the service. The function must not remove any existing items from the
// buffer. If the underlying RPC takes an int32 page size, pageSize should
// be silently truncated.
fetch func(pageSize int, pageToken string) (nextPageToken string, err error)
```

## Credential

The authorization between the client and the server should be independent
with authorization between the server and the database. A client should never
store any sensitive data such as DB username and password.
