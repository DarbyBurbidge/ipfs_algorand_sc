# What is it?
This is a smart contract that allows one to upload IPFS keys, and then allows someone to buy those keys

The current contract allows one to upload IPFS keys and then sell them using a single fee for the lot.
Initially I had planned on doing multiple keys, but it's unnecessary.

### The Idea
Someone wants to buy a set of files from you. You encrypt those files, zip them, and upload them to IPFS.
Take those IPFS keys and create a smart contract where you set the amount to be paid for the said files.
Once the contract receives payment, the contract would pass the payment on to the owner, and the owner would need to send a decryption key to the Buyer so they could unencrypt the files.

### Some issues
The above still leaves the Buyer vulnerable after sending payment; however, the blockchain is transparent, if encryption of the files doesn't happen then the Buyer could just find the IPFS keys on the blockchain and steal the files without payment.

Encryption is a necessary aspect of selling data to ensure the Buyer can't steal, but because of the transparent nature of the blockchain, the decryption key must be passed outside of the blockchain. The smart contract can't effectively verify this and does nothing to guarantee the Buyer is able to access the files.

##### Note
Even if the SC required the Buyer to acknowledge receiving the key before releasing funds, then what happens if the Buyer says no? We then get back to the situation where the Buyer can effectively steal from the Seller

### Conclusion
While interesting, I don't think there is a good way to utilize the blockchain to sell data without utilizing Web 2.0 tools. This makes moving to Web 3.0 seem unnecessary for this kind of application. 

### Resources
This was built using the youtube series:
[Algorand PyTeal Course](https://www.youtube.com/watch?v=V3d3VTlgMo8&list=PLpAdAjL5F75CNnmGbz9Dm_k-z5I6Sv9_x)

Much of the code came directly from that resource and it's associated repo. The IPFS Smart contract code as well as most of the ipfs testing code is my own however.




# Setup

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Install [Algorand sandbox](https://github.com/algorand/sandbox)
3. Start sandbox:
    ```txt
    $ ./sandbox testnet up -v
    ```
4. Install Python virtual environment in project folder:
    ```txt
    $ python -m venv venv
    $ source ./venv/Scripts/activate # Windows
    $ source ./venv/bin/activate # Linux
    ```
5. Use Python interpreter: `./venv/Scripts/python.exe`
    VSCode: `Python: Select Interpreter`

6. Add pytest.ini file with a testnet account mnemonic (this should be in the same folder as this README):
```ini
[pytest]
env =
    D:fund_account_mnemonic=a list of words that constitute a mnemonic
```
7. Use a testnet faucet to fund the account with the above mnemonic
8. Run tests:
```txt
pytest test/
```

Some tests will take a few seconds, entire suite should be ~30-45s

# Links

- [Official Algorand Smart Contract Guidelines](https://developer.algorand.org/docs/get-details/dapps/avm/teal/guidelines/)
- [PyTeal Documentation](https://pyteal.readthedocs.io/en/latest/index.html)
- [Algorand DevRel Example Contracts](https://github.com/algorand/smart-contracts)
