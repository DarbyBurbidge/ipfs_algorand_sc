from pyteal import *
from test_utils import dump_teal, compile_teal, write_schema

def approval():
    
    buyer = Bytes("buyer")
    payment_amount = Bytes("payment_amount")
    num_files = Bytes("num_files")
    i = ScratchVar(TealType.uint64)
    
    @Subroutine(TealType.none)
    def transfer_funds_to_owner():
        return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.receiver: Txn.accounts[1],
                    TxnField.amount: App.globalGet(payment_amount),
                    TxnField.fee: Int(0)  # use fee pooling
                }
            ),
            InnerTxnBuilder.Submit()
        )
    
    @Subroutine(TealType.none)
    def send_files():
        #i = ScratchVar(TealType.uint64)
        return Seq(
                InnerTxnBuilder.Begin(),
                For(i.store(Int(0)), i.load() < App.globalGet(num_files), i.store(i.load() + Int(1)))
                .Do(
                    Seq(
                        InnerTxnBuilder.SetFields(
                            {
                                TxnField.type_enum: TxnType.Payment,
                                TxnField.receiver: Txn.accounts[0],
                                TxnField.amount: Int(0),
                                TxnField.note: App.globalGet(Itob(i.load())),
                                TxnField.fee: Int(0)  # use fee pooling
                            }
                        ),
                        If(i.load() < App.globalGet(num_files) - Int(1))
                        .Then(
                            InnerTxnBuilder.Next()
                        ),
                    )
                ),
                InnerTxnBuilder.Submit()
            )
        
    @Subroutine(TealType.none)
    def close_sale():
        return Seq(
            For(i.store(Int(0)), i.load() < App.globalGet(num_files), i.store(i.load() + Int(1)))
            .Do(
                App.globalDel(Itob(i.load()))
            ),
            App.globalDel(num_files),
            App.globalDel(payment_amount),
            App.globalDel(buyer)
        )
        
    setup_shop = Seq(
        [
            App.globalPut(buyer, Txn.accounts[1]),
            App.globalPut(payment_amount, Btoi(Txn.application_args[0])),
            App.globalPut(num_files, Btoi(Txn.application_args[1])),
            For(i.store(Int(0)), i.load() < App.globalGet(num_files), i.store(i.load() + Int(1)))
            .Do(
                App.globalPut(Itob(i.load()), Txn.application_args[i.load() + Int(2)])
            ),
            Approve()
        ]
    )
    
    handle_purchase = Seq(
            [   
                Assert(
                    And(
                        # Make sure the first transaction is the payment
                        Gtxn[0].type_enum() == TxnType.Payment,
                        Gtxn[0].amount() >= App.globalGet(payment_amount),
                        Txn.fee() >= Global.min_txn_fee() * Int(3)
                    )
                ),
                transfer_funds_to_owner(),
                send_files(),
                close_sale(),
                Approve()
            ]
        )
    
    event_loop = event(
        init=Seq(
        [
            Approve()
        ]
    ), no_op=Cond(
        [Txn.accounts[0] == Global.creator_address(), setup_shop],
        [Txn.accounts[0] == App.globalGet(buyer), handle_purchase]
    ))
    return compileTeal(event_loop, Mode.Application, version=MAX_TEAL_VERSION)
    
def clear():
    return compileTeal(Reject(), Mode.Application, version=MAX_TEAL_VERSION)   

def compile_ipfs(client, num_files):
    dump_teal('ipfs_transfer_approval.teal', approval)
    dump_teal('ipfs_transfer_clear.teal', clear)
    
    compile_teal(client, approval(), 'ipfs_transfer_approval.compiled')
    compile_teal(client, clear(), 'ipfs_transfer_clear.compiled')
    
    write_schema(file_path='local_schema', num_ints=0, num_bytes=0)
    write_schema(file_path='global_schema', num_ints=2, num_bytes=num_files+1)
    
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