import base64
import json
import os
from algosdk import mnemonic, account
from algosdk.v2client import algod
from algosdk.future import transaction
from joblib import dump, load

# Set environment variables

# Loads the address and token config file for testing 
def load_config(path='./test_utils/test_config.json'):
    file = open(path)
    return json.load(file)


# Creates build directory if it does not exist
def check_build_dir():
    if not os.path.exists('build'):
        os.mkdir('build')

# Removes anything not listed inside .gitkeep from build folder
def clean_build():
    for file in os.scandir("./build"):
        if not file.path.endswith('.gitkeep'):
            os.remove(file.path)

def dump_teal(file_path, teal_program):
    check_build_dir()
    with open('./build/' + file_path, 'w') as f:
        teal = teal_program()
        f.write(teal)
        
def compile_teal(client, to_compile, file_path):
    compile_response = client.compile(to_compile)
    if file_path == None:
        return base64.b64decode(compile_response['result'])
    else:
        check_build_dir()
        dump(base64.b64decode(compile_response['result']), './build/' + file_path)
            
def load_compiled(file_path):
    try:
        compiled = load('./build/' + file_path)
    except:
        print("Error reading source file...exiting")
        exit(-1)
    return compiled

def write_schema(file_path, num_ints, num_bytes):
    f = open('./build/' + file_path, "w")
    json.dump({"num_ints": num_ints,
               "num_bytes": num_bytes}, f)
    f.close()

def load_schema(file_path):
    f = open('./build/' + file_path, 'r')
    stateJSON = json.load(f)
    return transaction.StateSchema(stateJSON['num_ints'], stateJSON['num_bytes'])

def get_global_state(client, address, app_id):
    account_info = client.account_info(address)
    output = {}
    created_apps = account_info['created-apps']
    for app in created_apps:
        if app['id'] == app_id and 'global-state' in app['params']:
            print(app)
            for key_value in app['params']['global-state']:
                if key_value['value']['type'] == 1:
                    value = key_value['value']['bytes']
                else:
                    value = key_value['value']['uint']
                output[base64.b64decode(key_value['key']).decode()] = value
            return output
        else:
            return None

def get_local_state(client, address, app_id):
    account_info = client.account_info(address)
    output = {}
    for app in account_info['apps-local-state']:
        if app['id'] == app_id:
            for key_value in app['key-value']:
                if key_value['value']['type'] == 1:
                    value = key_value['value']['bytes']
                else:
                    value = key_value['value']['uint']
                output[base64.b64decode(key_value['key']).decode()] = value
            return output
            
# Creates a new account and returns             
def generate_new_account():
    private_key, address = account.generate_account()
    return mnemonic.from_private_key(private_key), private_key, address

#gets the algod client from the alosdk            
def get_algod_client(token, address):
    return algod.AlgodClient(token, address)

#signs the unsigned transaction using the private key and returns a signed txn
def sign_txn(unsigned_txn, private_key):
    signed_tx = unsigned_txn.sign(private_key)
    return signed_tx

def app_signed_txn(
    private_key,
    creator_address,
    params,
    on_complete,
    approval_program,
    clear_program,
    global_schema,
    local_schema,
    app_args,
    pages=0):
    """
        Creates an signed "create app" transaction to an application
            Args:
                private_key (str): private key of sender
                creator_address (str): address of creator
                params (???): parameters obtained from algod
                on_complete (???):
                approval_program (???): compiled approval program
                clear_program (???): compiled clear program
                global_schema (???): global schema variables
                local_schema (???): local schema variables
            Returns:
                tuple: Tuple containing the signed transaction and signed transaction id
    """
    unsigned_txn = transaction.ApplicationCreateTxn(creator_address,
                                                    params,
                                                    on_complete,
                                                    approval_program,
                                                    clear_program,
                                                    global_schema,
                                                    local_schema,
                                                    app_args,
                                                    extra_pages=pages)
    signed_txn = sign_txn(unsigned_txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()

def payment_signed_txn(sender_private_key,
                       sender_address,
                       receiver_address,
                       amount,
                       params,
                       asset_id=None):
    """
    Creates and signs an "payment" transaction to an application, this works with algo or asa
    
        Args:
            sender_private_key (str): private key of sender
            sender_address (str): address of sender
            receiver_address (str): address of receiver
            amount (int): number of tokens/asset to send
            params (???): parameters obtained from algod
            asset_id (int): id of assets if any
        Returns:
            tuple: Tuple containing the signed transaction and signed transaction id
    """
    if asset_id is None:
        txn = transaction.PaymentTxn(sender_address,
                                     params,
                                     receiver_address,
                                     amount)

    else:
        txn = transaction.AssetTransferTxn(sender_address,
                                           params,
                                           receiver_address,
                                           amount,
                                           asset_id)

    signed_txn = sign_txn(txn, sender_private_key)
    return signed_txn, signed_txn.transaction.get_txid()

def wait_for_txn_confirm(client, transaction_id, timeout):
    """
    Wait until the transaction is confirmed or rejected, or until 'timeout'
    number of rounds have passed.
    
    Args:
        transaction_id (str): the transaction to wait for
        timeout (int): maximum number of rounds to wait
    Returns:
        dict: pending transaction information, or throws an error if the transaction
            is not confirmed or rejected in the next timeout rounds
    """
    start_round = client.status()["last-round"] + 1
    current_round = start_round

    while current_round < start_round + timeout:
        try:
            pending_txn = client.pending_transaction_info(transaction_id)
        except Exception:
            return
        if pending_txn.get("confirmed-round", 0) > 0:
            return pending_txn
        elif pending_txn["pool-error"]:
            raise Exception(
                'pool error: {}'.format(pending_txn["pool-error"])
            )
        client.status_after_block(current_round)
        current_round += 1
    raise Exception(
        'pending tx not found in timeout rounds, timeout value = : {}'.format(timeout))
            
def fund_account(receiver_address, sender_mnemonic, init_fund=1000000):
    """
    Sets initial amount of funds to the test account for testing
    
    Args:
        address (str): account address to fund
        sender_mnemonic (str): the mnemonic secret for the sender account
        init_fund (int, optional): amount to send. Defaults to 1000000.
    """
    test_config = load_config()
    priv_key = mnemonic.to_private_key(sender_mnemonic)
    sender_address = account.address_from_private_key(priv_key)
    client = get_algod_client(test_config['algod_token'], test_config['algod_address'])
    txn, txn_id = payment_signed_txn(
        priv_key,
        sender_address,
        receiver_address,
        init_fund,
        client.suggested_params(),
    )
    client.send_transaction(txn)
    wait_for_txn_confirm(client, txn_id, 5)

