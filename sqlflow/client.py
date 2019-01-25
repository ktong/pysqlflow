import os
import logging

import grpc
import google.protobuf.wrappers_pb2 as wrapper

import sqlflow.proto.sqlflow_pb2 as pb
import sqlflow.proto.sqlflow_pb2_grpc as pb_grpc

_LOGGER = logging.getLogger(__name__)


class Client:
    def __init__(self, server_url=None):
        """A minimum client that issues queries to and fetch results/logs from sqlflowserver.

        Args:
            server_url(str):    sqlflowserver url. If None, read value from environment
                                variable SQLFLOW_SERVER

        Raises:
            KeyError:
                Raised if SQLFLOW_SERVER is not specified as environment variable
        """
        if server_url is None:
            if "SQLFLOW_SERVER" not in os.environ:
                raise ValueError("Can't find environment variable SQLFLOW_SERVER")
            server_url = os.environ["SQLFLOW_SERVER"]

        print("server_url: {}".format(server_url))
        # FIXME(tonyyang-svail): change insecure_channel to secure_channel
        channel = grpc.insecure_channel(server_url)
        self._stub = pb_grpc.SQLFlowStub(channel)

    def execute(self, operation):
        """Run a SQLFlow operation

        Argument:
            operation(str): SQL query to be executed.

        Returns:
            Generator: generates the response of the server
        """
        for res in self._stub.Run(pb.RunRequest(sql=operation)):
            if res.WhichOneof('response') == 'messages':
                for message in res.messages.messages:
                    yield message
            else:
                yield self._decode_protobuf(res)

    @classmethod
    def _decode_protobuf(cls, res):
        """Decode Server Response

        Args:
            res(sqlflow.proto.sqlflow_pb2.RunResponse.Columns)

        Returns:
            Dictionary from str to list
        """
        table = {"column_names": [name for name in res.table.column_names],
                 "rows": [[cls._decode_any(a) for a in row.data] for row in res.table.rows]}
        return table

    @classmethod
    def _decode_any(cls, any_message):
        """Decode a google.protobuf.any_pb2

        Argument: any_message(google.protobuf.any_pb2): any message

        Returns: any python object
        """
        try:
            message = next(getattr(wrapper, type_name)()
                           for type_name, desc in wrapper.DESCRIPTOR.message_types_by_name.items()
                           if any_message.Is(desc))
            any_message.Unpack(message)
            return message.value
        except StopIteration:
            raise TypeError("Unsupported type {}".format(any_message))
