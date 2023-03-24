
from algosdk import account, encoding, mnemonic
from algosdk.future import transaction
from test_utils import get_algod_client, app_signed_txn, wait_for_txn_confirm, load_compiled, load_schema, ipfscidv0_to_byte32

def deploy_ipfs_app(client, priv_key, approval_prog, clear_prog, global_schema, local_schema, app_args):
    
    # Get address of sender
    creator_address = account.address_from_private_key(priv_key)
    
    # Set on_complete to NoOp
    on_complete = transaction.OnComplete.NoOpOC.real
    
    # Get suggested parameters
    params = client.suggested_params()
    
    # Create transaction
    signed_txn, txn_id = app_signed_txn(
        priv_key,
        creator_address,
        params,
        on_complete,
        approval_prog,
        clear_prog,
        global_schema,
        local_schema,
        app_args
    )
    
    # Send the txn
    client.send_transactions([signed_txn])
    
    # Wait for txn to confirm or throw after 5 rounds
    wait_for_txn_confirm(client, txn_id, 5)
    
    # Get app_id and print a success message
    txn_response = client.pending_transaction_info(txn_id)
    app_id = txn_response['application-index']
    print("Deployed new app: " + str(app_id))
    print("Deployed app address: " + 
          encoding.encode_address(encoding.checksum(b'appID' + app_id.to_bytes(8, 'big'))))
    
    return app_id
    

def deploy_ipfs(algod_address, algod_token, creator_mnemonic, num_items, sum_item_cost, list_ipfs_keys):
    priv_key = mnemonic.to_private_key(creator_mnemonic)
    algod_client = get_algod_client(algod_token, algod_address)
    
    approval_prog = load_compiled(file_path='ipfs_transfer_approval.compiled')
    clear_prog = load_compiled(file_path='ipfs_transfer_clear.compiled')
    
    global_schema = load_schema(file_path='global_schema')
    local_schema = load_schema(file_path='local_schema')
    
    app_args = []
    app_args.append(num_items)
    app_args.append(sum_item_cost)

    for file_key in list_ipfs_keys:
        app_args.append(ipfscidv0_to_byte32(file_key))
    print(app_args)
    
    app_id = deploy_ipfs_app(
        algod_client,
        priv_key,
        approval_prog,
        clear_prog,
        global_schema,
        local_schema,
        app_args
    )
    
    return app_id