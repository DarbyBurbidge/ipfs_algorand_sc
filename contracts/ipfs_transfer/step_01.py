from pyteal import *
from test_utils import dump_teal, compile_teal, write_schema

def approval():
    file_1 = Bytes("file_1")
    
    event_loop = event(init=Seq(
        [
            App.globalPut(file_1, Txn.application_args[0]),
            Approve()
        ]
    ))
    return compileTeal(event_loop, Mode.Application, version=5)
    
def clear():
    return compileTeal(Reject(), Mode.Application, version=5)   

def compile_ipfs(client, num_files):
    dump_teal('ipfs_transfer_approval.teal', approval)
    dump_teal('ipfs_transfer_clear.teal', clear)
    
    compile_teal(client, approval(), 'ipfs_transfer_approval.compiled')
    compile_teal(client, clear(), 'ipfs_transfer_clear.compiled')
    
    write_schema(file_path='local_schema', num_ints=0, num_bytes=0)
    write_schema(file_path='global_schema', num_ints=0, num_bytes=num_files)
    
def event(
    init: Expr = Reject(),
    delete: Expr = Reject(),
    update: Expr = Reject(),
    opt_in: Expr = Reject(),
    close_out: Expr = Reject(),
    no_op: Expr = Reject(),
) -> Expr:
    return Cond(
        [Txn.application_id() == Int(0), init],
        [Txn.on_completion() == OnComplete.DeleteApplication, delete],
        [Txn.on_completion() == OnComplete.UpdateApplication, update],
        [Txn.on_completion() == OnComplete.OptIn, opt_in],
        [Txn.on_completion() == OnComplete.CloseOut, close_out],
        [Txn.on_completion() == OnComplete.NoOp, no_op],
    )