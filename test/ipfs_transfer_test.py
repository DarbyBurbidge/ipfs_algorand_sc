import os
from tokenize import String
import pytest
import base64
from test_utils import load_schema, get_global_state, get_local_state, ipfscidv0_to_byte32, payment_signed_txn, wait_for_txn_confirm, sign_txn, byte32_to_ipfscidv0
from algosdk.future import transaction
from algosdk.v2client import algod
from algosdk import encoding

DEFAULT_STATE_BYTES=1
DEFAULT_STATE_INTS=2
TEST_NUM_FILES=1
TEST_IPFS_KEY=["QmcasS8sQuasoFb2MDXbmBDwatWdhbkXrmx7131Rban9GG"]
TOTAL_ITEM_COST=300000
NOOP_FEE=3000

@pytest.fixture(scope='class')
def test_config():
    from test_utils import load_config
    return load_config()

@pytest.fixture(scope='class')
def client(test_config):
    algod_address = test_config['algod_address']
    algod_token = test_config['algod_token']
    client = algod.AlgodClient(algod_token, algod_address)
    return client

@pytest.fixture(scope='class')
def wallet_1():
    from test_utils import generate_new_account, fund_account
    mnemonic, priv_key, address = generate_new_account()
    
    wallet_1 = {'mnemonic': mnemonic, 'address': address, 'priv_key': priv_key}
    
    fund_account(wallet_1['address'], os.getenv('fund_account_mnemonic'))
    print(wallet_1)
    return wallet_1

@pytest.fixture(scope='class')
def wallet_2():
    from test_utils import generate_new_account, fund_account
    mnemonic, priv_key, address = generate_new_account()
    
    wallet_2 = {'mnemonic': mnemonic, 'address': address, 'priv_key': priv_key}
    
    fund_account(wallet_2['address'], os.getenv('fund_account_mnemonic'))
    return wallet_2

@pytest.fixture(scope='class')
def app_id(test_config, wallet_1):
    from contracts.ipfs_transfer.deploy import deploy_ipfs
    
    algod_address = test_config['algod_address']
    algod_token = test_config['algod_token']
    creator_mnemonic = wallet_1['mnemonic']
    app_id = deploy_ipfs(algod_address, algod_token, creator_mnemonic, TEST_NUM_FILES, TOTAL_ITEM_COST, TEST_IPFS_KEY)
    return app_id

class TestIPFSTransfer:
    def test_env(self):
        assert os.getenv('fund_account_mnemonic') != None
    
    def test_build(self, client):
        from contracts.ipfs_transfer.step_01 import compile_ipfs
        from test_utils import check_build_dir, clean_build
        check_build_dir()
        clean_build()
        import os
        compile_ipfs(client, TEST_NUM_FILES)
        assert os.path.exists('./build/ipfs_transfer_approval.compiled')
        assert os.path.exists('./build/ipfs_transfer_clear.compiled')
        assert os.path.exists('./build/ipfs_transfer_approval.teal')
        assert os.path.exists('./build/ipfs_transfer_clear.teal')
        assert os.path.exists('./build/global_schema')
        assert os.path.exists('./build/local_schema')
        
        
    def test_schema(self):
        global_schema = load_schema('global_schema')
        local_schema = load_schema('local_schema')
        assert global_schema == transaction.StateSchema(DEFAULT_STATE_INTS, TEST_NUM_FILES + DEFAULT_STATE_BYTES)
        assert local_schema == transaction.StateSchema(0, 0)
        
    def test_deploy(self, app_id, client, wallet_1):
        assert app_id
        sender_address = wallet_1['address']
        global_state = get_global_state(client, sender_address, app_id) 
        local_state = get_local_state(client, sender_address, app_id)
        assert_state(local_state, global_state, None, None)
        
    def test_shop_setup(self, client, app_id, wallet_1, wallet_2):
        params = client.suggested_params()
        #app_address = encoding.encode_address(encoding.checksum(b'appID' + app_id.to_bytes(8, 'big')))
        
        # Prepare NoOp transaction from the creator (business) address
        # Adds ipfs keys to the SC for purchase by buyer
        # Limit is 13 keys at a time (arg limit)
        # total of 61 keys total on a single SC for purchase (3 global states locked up in TotalCost, BuyerAddress, and NumItems)
        txn_args = [TOTAL_ITEM_COST, TEST_NUM_FILES]
        for key in TEST_IPFS_KEY:
            txn_args.append(ipfscidv0_to_byte32(key))
        assert len(txn_args) == 3
        txn_prepare_purchase = transaction.ApplicationNoOpTxn(
            wallet_1['address'], 
            params,
            app_id, 
            txn_args,
            [wallet_2['address']]
        )
        print(txn_prepare_purchase)
        
        signed_setup_txn = sign_txn(txn_prepare_purchase, wallet_1['priv_key'])
        setup_id = signed_setup_txn.transaction.get_txid()
        
        client.send_transactions([signed_setup_txn])
        
        wait_for_txn_confirm(client, setup_id, 5)
        
        # Get responses
        noop_response = client.pending_transaction_info(setup_id)
        
        assert noop_response
        
        
    def test_state_after_setup(self, client, app_id, wallet_1, wallet_2):
        assert app_id
        
        sender_address = wallet_1['address']
        global_state = get_global_state(client, sender_address, app_id)
        local_state = get_local_state(client, sender_address, app_id)
        
        expected_global = {
            "buyer": base64.b64encode(encoding.decode_address(wallet_2['address'])).decode('utf-8'),
            "payment_amount": TOTAL_ITEM_COST,
            "num_files": TEST_NUM_FILES
        }
        
        for i in range(0, TEST_NUM_FILES):
            expected_global[i.to_bytes(8, 'big').decode()] = base64.b64encode(ipfscidv0_to_byte32(TEST_IPFS_KEY[i]).encode('utf-8')).decode('utf-8')
           
        assert_state(local_state, global_state, None, expected_global)

        
          
    def test_purchase(self, client, app_id, wallet_1, wallet_2):
        
        params = client.suggested_params()
        
        app_address = encoding.encode_address(encoding.checksum(b'appID' + app_id.to_bytes(8, 'big')))
        # Create txns
        txn_pay = transaction.PaymentTxn(wallet_2['address'], params, app_address, TOTAL_ITEM_COST + 100000)

        # Make sure noop fee covers inner txns    
        txn_noop = transaction.ApplicationNoOpTxn(wallet_2['address'], params, app_id)
        txn_noop.fee = NOOP_FEE
        txn_noop.accounts = [wallet_1['address']]
        print(txn_noop)
        
        # Group txns
        gid = transaction.calculate_group_id([txn_pay, txn_noop])
        txn_pay.group = gid
        txn_noop.group = gid
        # Check txns have the same group
        assert txn_noop.group == txn_pay.group
        
        #sign the txns
        signed_pay = sign_txn(txn_pay, wallet_2['priv_key'])
        pay_id = signed_pay.transaction.get_txid()
        signed_noop = sign_txn(txn_noop, wallet_2['priv_key'])
        noop_id = signed_noop.transaction.get_txid()
        
        #regroup txns
        signed_group = [signed_pay, signed_noop]
        
        # Send the txn
        client.send_transactions(signed_group)
        
        # Wait for txn to confirm or throw after 5 rounds
        wait_for_txn_confirm(client, noop_id, 5)
        wait_for_txn_confirm(client, pay_id, 5)
        
        # Get responses
        noop_response = client.pending_transaction_info(noop_id)
        pay_response = client.pending_transaction_info(pay_id)
        
        #if there's an error, give a printout of the txn
        print (noop_response['inner-txns'])
        inner_pay_txn = noop_response['inner-txns'][0]['txn']['txn']
        inner_key_txn = noop_response['inner-txns'][1]['txn']['txn']
        # Make sure payment went to the right place and right amount
        assert inner_pay_txn['rcv'] == wallet_1['address'] 
        assert inner_pay_txn['amt'] == TOTAL_ITEM_COST
        # Make sure the inner transaction sent the right key
        assert base64.b64decode(inner_key_txn['note']).decode() == ipfscidv0_to_byte32(TEST_IPFS_KEY[0])
        # Make sure the key was sent to the right account
        assert inner_key_txn['rcv'] == wallet_2['address']
        
    def test_state_after_close(self, app_id, client, wallet_1):
        assert app_id
        sender_address = wallet_1['address']
        global_state = get_global_state(client, sender_address, app_id) 
        local_state = get_local_state(client, sender_address, app_id)
        assert_state(local_state, global_state, None, None)
     
      
    
    
        
        
def assert_state(local_state, global_state, expected_local, expected_global):
    #assert len(global_state) == TEST_NUM_FILES + DEFAULT_STATE_BYTES + DEFAULT_STATE_INTS
    if expected_local == None:
        assert local_state == None
    else:
        assert len(local_state) == len(expected_local.leys())
        for key in expected_local.keys():
            assert key in local_state.keys()
            assert local_state[key] == expected_local[key]
        
    if expected_global== None:
        assert global_state == None
    else:
        assert len(global_state) == len(expected_global.keys()) 
        for key in expected_global.keys():
            assert key in global_state.keys()
            assert global_state[key] == expected_global[key]