import os
import pytest
import base64
from test_utils import load_schema, get_global_state, get_local_state, ipfscidv0_to_byte32, byte32_to_ipfscidv0
from algosdk.future import transaction
from algosdk.v2client import algod

TEST_NUM_FILES=1
TEST_IPFS_KEY=["QmcasS8sQuasoFb2MDXbmBDwatWdhbkXrmx7131Rban9GG"]

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
    return wallet_1

@pytest.fixture(scope='class')
def wallet_2():
    from test_utils import generate_new_account, fund_account
    mnemonic, priv_key, address = generate_new_account()
    
    wallet_2 = {'mnemonic': mnemonic, 'address': address, 'priv_key': priv_key}
    
    fund_account(wallet_1['address'], os.getenv('fund_account_mnemonic'))
    return wallet_2

@pytest.fixture(scope='class')
def app_id(test_config, wallet_1):
    from contracts.ipfs_transfer.deploy import deploy_ipfs
    
    algod_address = test_config['algod_address']
    algod_token = test_config['algod_token']
    creator_mnemonic = wallet_1['mnemonic']
    app_id = deploy_ipfs(algod_address, algod_token, creator_mnemonic, TEST_IPFS_KEY)
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
        assert global_schema == transaction.StateSchema(0, TEST_NUM_FILES)
        assert local_schema == transaction.StateSchema(0, 0)
     
      
    def test_deploy(self, app_id, client, wallet_1):
        assert app_id
        sender_address = wallet_1['address']
        global_state = get_global_state(client, sender_address, app_id)
        local_state = get_local_state(client, sender_address, app_id)
        assert_state(local_state, global_state, TEST_IPFS_KEY[0])
    
        
        
def assert_state(local_state, global_state, file_id):
    assert local_state == None
    assert len(global_state) == 1
    
    expected_vars = {
        "file_1": file_id
    }
    
    for key in expected_vars.keys():
        assert key in global_state.keys()
    assert base64.b64decode(global_state[key]).decode() == ipfscidv0_to_byte32(expected_vars[key])
    